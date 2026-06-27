---
name: iii-agent-observability
description: >-
  Use when adding LLM tracing, evaluation, and scoring to iii: capturing traces and spans for
  LLM calls and agent steps, attaching token/cost/latency metadata to function traces, running
  hallucination and relevance metrics, wiring eval as triggers on completion events, and
  surfacing RAG and agent observability in the iii console.
---

# Agent Observability

Observability for LLM and agent workloads on iii. Each LLM call or agent step is an iii function
trace; spans, token usage, cost, latency, and eval scores ride along as function and trigger
metadata, then stream into the `iii-observability` worker and console.

This is the native iii pattern for the capability that `comet-ml/opik` provides: trace LLM
applications, score RAG and agentic workflows, and dash the results.

## Model Map

| Opik concept | iii shape |
| --- | --- |
| Trace | Top-level function invocation, e.g. `agent::answer` |
| Span | Child `trigger()` call (LLM call, retrieval, tool step) |
| Trace tags / feedback scores | `metadata` on functions and triggers |
| Online evaluation rule | `eval::*` function bound by a completion-event trigger |
| Project dashboard | `iii-observability` worker plus the console |

Keep raw prompts and completions in payloads or state; keep only numbers, ids, and labels in
metadata. Do not put secrets or full prompt text in metadata.

## Trace and Span Metadata

Attach observability fields as metadata so the registry and `iii-observability` worker can index
them. Recommended keys:

| Key | Meaning |
| --- | --- |
| `observability.kind` | `llm`, `retrieval`, `tool`, or `agent` |
| `observability.model` | Model id used for the span |
| `observability.tokens` | `{ input, output, total }` |
| `observability.cost_usd` | Estimated cost for the span |
| `observability.latency_ms` | Wall-clock duration |
| `observability.score` | Last eval score, 0..1 |

## Instrumenting LLM Calls

Wrap each model call as a function and emit a span record to the observability worker.

### TypeScript

```typescript
import { registerWorker, TriggerAction } from "iii-sdk";

const iii = registerWorker("ws://localhost:49134", { workerName: "llm-worker" });

iii.registerFunction(
  "llm::complete",
  async ({ model, prompt, traceId }) => {
    const started = Date.now();
    const res = await callModel(model, prompt);
    const span = {
      traceId,
      kind: "llm",
      model,
      tokens: res.usage,
      cost_usd: estimateCost(model, res.usage),
      latency_ms: Date.now() - started,
    };
    await iii.trigger({
      function_id: "observability::span",
      payload: span,
      action: TriggerAction.Void(),
    });
    return { traceId, text: res.text, usage: res.usage };
  },
  { metadata: { "observability.kind": "llm" } },
);
```

### Python

```python
import time
from iii import register_worker

iii = register_worker("ws://localhost:49134")

def complete(req):
    started = time.time()
    res = call_model(req["model"], req["prompt"])
    span = {
        "traceId": req["traceId"],
        "kind": "llm",
        "model": req["model"],
        "tokens": res["usage"],
        "cost_usd": estimate_cost(req["model"], res["usage"]),
        "latency_ms": int((time.time() - started) * 1000),
    }
    iii.trigger({
        "function_id": "observability::span",
        "payload": span,
        "action": {"type": "void"},
    })
    return {"traceId": req["traceId"], "text": res["text"], "usage": res["usage"]}

iii.register_function("llm::complete", complete, metadata={"observability.kind": "llm"})
```

## The `llm-eval` Worker

Register an `llm-eval` worker that exposes scoring functions. Each returns a `0..1` score plus a
reason. Bind them as online rules, or call them synchronously inside an agent.

| Function | Scores |
| --- | --- |
| `eval::score` | Generic LLM-as-judge score against a rubric |
| `eval::hallucination` | Output unsupported by provided context |
| `eval::relevance` | Answer relevance to the question |

```typescript
const iii = registerWorker("ws://localhost:49134", { workerName: "llm-eval" });

iii.registerFunction(
  "eval::hallucination",
  async ({ question, context, answer }) => {
    const verdict = await judge("hallucination", { question, context, answer });
    return { metric: "hallucination", score: verdict.score, reason: verdict.reason };
  },
  { metadata: { "observability.kind": "eval", "eval.metric": "hallucination" } },
);

iii.registerFunction("eval::relevance", async ({ question, answer }) => {
  const verdict = await judge("relevance", { question, answer });
  return { metric: "relevance", score: verdict.score, reason: verdict.reason };
});
```

## Online Evaluation Triggers

Run eval automatically when an agent completes. Publish a completion event from the agent, then
bind eval functions to it and write the score back into the trace.

```typescript
iii.registerFunction("agent::answer", async (task) => {
  const out = await runAgent(task);
  await iii.trigger({
    function_id: "publish",
    payload: { topic: "agent.completed", data: { traceId: task.traceId, ...out } },
  });
  return out;
});

iii.registerFunction("eval::on-completion", async (event) => {
  const score = await iii.trigger({
    function_id: "eval::relevance",
    payload: { question: event.question, answer: event.answer },
  });
  await iii.trigger({
    function_id: "observability::score",
    payload: { traceId: event.traceId, metric: score.metric, score: score.score },
    action: TriggerAction.Void(),
  });
  return score;
});

iii.registerTrigger({
  type: "subscribe",
  function_id: "eval::on-completion",
  config: { topic: "agent.completed" },
  metadata: { "observability.kind": "eval" },
});
```

### Python trigger binding

```python
iii.register_trigger({
    "type": "subscribe",
    "function_id": "eval::on-completion",
    "config": {"topic": "agent.completed"},
    "metadata": {"observability.kind": "eval"},
})
```

Use `condition_function_id` on the trigger config to sample only a fraction of traces when eval is
expensive.

## Surfacing in the Console

The `iii-observability` worker ingests `observability::span` and `observability::score` calls and
exposes them to the console. Install it from the registry and replay with the rest of your stack:

```bash
iii worker add iii-observability
iii worker sync
```

Discover live eval and LLM functions through the engine registry:

| Function | Returns |
| --- | --- |
| `engine::functions::list` | Filter by `observability.kind` to find traced functions |
| `engine::triggers::list` | Find bound `eval::*` completion rules |

## When to Use

- Use this skill to trace LLM calls and agent steps, attach token/cost/latency metadata, run
  hallucination/relevance/score metrics, and wire eval as completion triggers.
- Use this for RAG and agentic observability that should appear in the iii console.

## Boundaries

- For function, trigger, and metadata syntax, use `iii-core-primitives`.
- For full agent pipeline composition, use `iii-architecture-patterns`.
- For observability worker config and ports, use `iii-engine-config`.
- For eval failures, timeouts, and retryability, use `iii-error-handling`.
