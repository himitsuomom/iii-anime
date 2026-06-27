---
name: iii-agent-routing
description: >-
  Use when routing LLM requests across multiple providers, building fallback and failover chains,
  selecting models by cost or latency, handling provider rate limits, or exposing a unified LLM
  gateway endpoint that existing agents and tools point at.
---

# Agent Routing

A `llm-router` worker turns scattered provider SDK calls into iii functions. Agents stop holding
provider keys and model logic; they call one of:

| Function | Payload | Returns |
| --- | --- | --- |
| `llm::complete` | `{ prompt, model?, max_tokens?, budget? }` | `{ text, model, provider, usage }` |
| `llm::chat` | `{ messages, model?, tools?, budget? }` | `{ message, model, provider, usage }` |
| `llm::embed` | `{ input, model? }` | `{ vectors, model, provider }` |

Routing, fallback, cost/latency selection, and provider failover live inside the worker. Callers
pass intent (`model` class or `budget`), not a provider. Bind one `http` trigger so external agents
and tools point at a single endpoint.

## Routing Model

The worker keeps a provider table and picks a candidate chain per request. `model` may name a
concrete model or a class (`"fast"`, `"cheap"`, `"reasoning"`); the router expands a class into an
ordered candidate list.

| Concern | Mechanism |
| --- | --- |
| Best/cheapest pick | Sort candidates by `cost_per_1k` then `p50_latency_ms` |
| Fallback chain | Ordered candidate list; advance on error or timeout |
| Provider failover | Per-attempt `timeout` plus retry across the next candidate |
| Rate-limit handling | On HTTP 429, enqueue the request to a queue trigger instead of failing |
| Per-caller RBAC + budget | Read `metadata` (caller id, allowed providers, max spend) before dispatch |

Provider endpoints are registered as HTTP-invoked functions so the engine owns timeout/retry. The
router function calls them by ID and walks the chain.

## Provider Functions (HTTP-invoked)

Register each upstream once. Use env var names for auth, never raw keys.

```typescript
import { registerWorker, TriggerAction } from "iii-sdk";

const iii = registerWorker("ws://localhost:49134", { workerName: "llm-router" });

// Upstream provider endpoints as HTTP-invoked functions.
iii.registerFunction("llm::provider::openai", {
  url: "https://api.openai.com/v1/chat/completions",
  method: "POST",
  headers: { Authorization: "Bearer ${OPENAI_API_KEY}", "Content-Type": "application/json" },
});

iii.registerFunction("llm::provider::anthropic", {
  url: "https://api.anthropic.com/v1/messages",
  method: "POST",
  headers: { "x-api-key": "${ANTHROPIC_API_KEY}", "anthropic-version": "2023-06-01" },
});
```

## Router Function (TypeScript)

```typescript
const TABLE = {
  cheap: [
    { id: "llm::provider::openai", model: "gpt-4o-mini", costPer1k: 0.15 },
    { id: "llm::provider::anthropic", model: "claude-haiku", costPer1k: 0.25 },
  ],
};

iii.registerFunction(
  "llm::chat",
  async (req, ctx) => {
    const rbac = ctx?.metadata ?? {};                       // caller id, allowed, maxSpend
    const candidates = (TABLE[req.model ?? "cheap"] ?? [])
      .filter((c) => !rbac.allowed || rbac.allowed.includes(c.id))
      .sort((a, b) => a.costPer1k - b.costPer1k);

    let lastErr;
    for (const c of candidates) {
      try {
        // Per-attempt timeout; engine retries are configured below.
        const res = await iii.trigger({
          function_id: c.id,
          payload: { model: c.model, messages: req.messages, tools: req.tools },
          timeout: 30_000,
        });
        return { message: res.choices?.[0]?.message ?? res, model: c.model, provider: c.id, usage: res.usage };
      } catch (err) {
        if (err.status === 429) {
          // Shed load: re-run later through a queue instead of burning the chain.
          await iii.trigger({
            function_id: "llm::chat",
            payload: req,
            action: TriggerAction.Enqueue({ queue: "llm-overflow" }),
          });
          throw err;
        }
        lastErr = err;                                       // advance to next candidate on failure
      }
    }
    throw lastErr ?? new Error("no candidate provider available");
  },
  { retry: { max_attempts: 2 }, timeout: 90_000, metadata: { owner: "platform", budget: true } },
);

// Single endpoint every agent/tool points at.
iii.registerTrigger({
  type: "http",
  function_id: "llm::chat",
  config: { api_path: "/llm/chat", http_method: "POST" },
});

// Drain rate-limited overflow back through the router.
iii.registerTrigger({
  type: "durable:subscriber",
  function_id: "llm::chat",
  config: { topic: "llm-overflow" },
});
```

## Router Function (Python)

```python
from iii import register_worker

iii = register_worker("ws://localhost:49134")

TABLE = {
    "cheap": [
        {"id": "llm::provider::openai", "model": "gpt-4o-mini", "cost": 0.15},
        {"id": "llm::provider::anthropic", "model": "claude-haiku", "cost": 0.25},
    ],
}

def chat(req, ctx=None):
    rbac = (ctx or {}).get("metadata", {})
    candidates = sorted(
        (c for c in TABLE.get(req.get("model", "cheap"), [])
         if not rbac.get("allowed") or c["id"] in rbac["allowed"]),
        key=lambda c: c["cost"],
    )
    last_err = None
    for c in candidates:
        try:
            res = iii.trigger({
                "function_id": c["id"],
                "payload": {"model": c["model"], "messages": req["messages"]},
                "timeout": 30_000,
            })
            return {"message": res["choices"][0]["message"], "model": c["model"], "provider": c["id"]}
        except Exception as err:
            if getattr(err, "status", None) == 429:
                iii.trigger({
                    "function_id": "llm::chat",
                    "payload": req,
                    "action": {"type": "enqueue", "queue": "llm-overflow"},
                })
                raise
            last_err = err
    raise last_err or RuntimeError("no candidate provider available")

iii.register_function("llm::chat", chat, {"retry": {"max_attempts": 2}, "timeout": 90_000})
iii.register_trigger({
    "type": "http",
    "function_id": "llm::chat",
    "config": {"api_path": "/llm/chat", "http_method": "POST"},
})
```

## Notes

- The chain handles routing decisions; the engine handles delivery. Keep per-attempt `timeout` short
  so failover is fast, and let function-level `retry` cover transient upstream faults.
- Enqueue on 429 only; on hard provider errors advance to the next candidate immediately.
- Put caller id, allowed providers, and spend caps in `metadata`. Read budget at dispatch and reject
  before calling a provider. Never store API keys in metadata; use env var names in HTTP config.
- `llm::complete` and `llm::embed` follow the same shape: candidate table, cost/latency sort, chain
  walk, one HTTP trigger each.

## Boundaries

- For function registration, trigger shapes, invocation modes, and HTTP-invoked function config, use
  `iii-core-primitives`.
- For queue retry policy, worker manager, and RBAC listeners, use `iii-engine-config`.
- For timeout, retryability, and RBAC denial handling, use `iii-error-handling`.
