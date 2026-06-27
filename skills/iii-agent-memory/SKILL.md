---
name: iii-agent-memory
description: >-
  Use when building agent long-term memory, recall, or a context engine on iii: a memory worker
  exposing memory::add, memory::search, memory::get, and memory::forget over iii state plus a
  vector/embedding store, with triggers that capture memories automatically from stream or queue
  events and inject recalled context into agent prompts. Covers embeddings, semantic search,
  sync recall vs enqueued capture, and namespacing memories per agent or user.
---

# Agent Memory

A memory + context engine for agents, modeled on the supermemory pattern, built as a native iii
worker. Memories are text fragments with embeddings, stored in iii state, and retrieved by semantic
search. The worker exposes four functions and binds triggers for automatic capture and recall.

| Function | Shape | Use for |
| --- | --- | --- |
| `memory::add` | `{ namespace, text, metadata? }` | Persist a memory and its embedding |
| `memory::search` | `{ namespace, query, k? }` | Top-k semantic recall for a query |
| `memory::get` | `{ namespace, id }` | Fetch one memory by id |
| `memory::forget` | `{ namespace, id }` | Delete a memory |

Namespace scopes memories per agent, user, or session. Keep it in every call so recall never
crosses tenants.

## Storage Model

Each memory is a state entry under scope `memory:<namespace>` keyed by a generated id. The value
holds `{ text, embedding, metadata, created_at }`. `memory::search` embeds the query, scores every
entry by cosine similarity, and returns the top `k`. Swap the brute-force scan for a vector worker
(`vector::upsert` / `vector::query`) once the namespace grows past a few thousand entries; the
function contract stays the same.

| Concern | Default | Scale path |
| --- | --- | --- |
| Vectors | iii state scope per namespace | dedicated vector worker |
| Embeddings | `embed::text` function | batch via `TriggerAction.Enqueue` |
| Recall ranking | cosine over candidates | ANN index in vector worker |

## Invocation Modes

| Mode | Call | Use when |
| --- | --- | --- |
| Sync recall | `trigger({ function_id: "memory::search", payload })` | Agent needs context before responding |
| Enqueue capture | `TriggerAction.Enqueue({ queue: "memory" })` | Persisting a memory off the hot path |
| Void capture | `TriggerAction.Void()` | Best-effort capture, result ignored |

Recall is synchronous because the agent blocks on it. Capture is enqueued so embedding latency and
write retries never slow the conversation.

## Automatic Capture and Recall

Bind a `stream` or `durable:subscriber` trigger so any agent turn pushed onto a stream is captured
without explicit calls. Bind `http` for an explicit recall endpoint that injects context into a
prompt.

| Trigger | Config | Effect |
| --- | --- | --- |
| `stream` | `{ stream_name: "agent.turns", group_id: "memory" }` | Capture each turn as a memory |
| `durable:subscriber` | `{ topic: "memory.capture" }` | Capture published memory events |
| `http` | `{ api_path: "/recall", http_method: "POST" }` | Recall + prompt assembly on demand |

## TypeScript

```typescript
import { registerWorker, TriggerAction } from "iii-sdk";

const iii = registerWorker("ws://localhost:49134", { workerName: "memory-worker" });

const scope = (ns: string) => `memory:${ns}`;
const cosine = (a: number[], b: number[]) => {
  let dot = 0, na = 0, nb = 0;
  for (let i = 0; i < a.length; i++) { dot += a[i] * b[i]; na += a[i] ** 2; nb += b[i] ** 2; }
  return dot / (Math.sqrt(na) * Math.sqrt(nb) + 1e-9);
};

iii.registerFunction("memory::add", async ({ namespace, text, metadata }) => {
  const [embedding] = await iii.trigger({ function_id: "embed::text", payload: { input: [text] } });
  const id = crypto.randomUUID();
  await iii.trigger({
    function_id: "state::set",
    payload: { scope: scope(namespace), key: id,
      value: { text, embedding, metadata: metadata ?? {}, created_at: Date.now() } },
  });
  return { id };
});

iii.registerFunction("memory::search", async ({ namespace, query, k = 5 }) => {
  const [q] = await iii.trigger({ function_id: "embed::text", payload: { input: [query] } });
  const entries = await iii.trigger({ function_id: "state::list", payload: { scope: scope(namespace) } });
  return entries
    .map((e: any) => ({ id: e.key, text: e.value.text, metadata: e.value.metadata,
      score: cosine(q, e.value.embedding) }))
    .sort((a: any, b: any) => b.score - a.score)
    .slice(0, k);
});

iii.registerFunction("memory::get", async ({ namespace, id }) =>
  iii.trigger({ function_id: "state::get", payload: { scope: scope(namespace), key: id } }));

iii.registerFunction("memory::forget", async ({ namespace, id }) => {
  await iii.trigger({ function_id: "state::delete", payload: { scope: scope(namespace), key: id } });
  return { forgotten: id };
});

// Recall injected into an agent prompt over HTTP.
iii.registerFunction("agent::respond", async ({ namespace, message }) => {
  const recalled = await iii.trigger({
    function_id: "memory::search", payload: { namespace, query: message, k: 5 },
  });
  const context = recalled.map((m: any) => `- ${m.text}`).join("\n");
  const reply = await iii.trigger({
    function_id: "llm::complete",
    payload: { prompt: `Relevant memory:\n${context}\n\nUser: ${message}` },
  });
  // Capture the exchange off the hot path.
  await iii.trigger({
    function_id: "memory::add",
    payload: { namespace, text: `User: ${message}\nAssistant: ${reply}` },
    action: TriggerAction.Enqueue({ queue: "memory" }),
  });
  return { reply };
});

iii.registerTrigger({
  type: "http",
  function_id: "agent::respond",
  config: { api_path: "/recall", http_method: "POST" },
});

// Capture every agent turn streamed elsewhere, no explicit add call.
iii.registerTrigger({
  type: "stream",
  function_id: "memory::add",
  config: { stream_name: "agent.turns", group_id: "memory" },
});
```

## Python

```python
import math, uuid, time
from iii import register_worker

iii = register_worker("ws://localhost:49134")

def scope(ns): return f"memory:{ns}"

def cosine(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb + 1e-9)

def add(payload):
    text = payload["text"]
    embedding = iii.trigger({"function_id": "embed::text", "payload": {"input": [text]}})[0]
    mid = str(uuid.uuid4())
    iii.trigger({"function_id": "state::set", "payload": {
        "scope": scope(payload["namespace"]), "key": mid,
        "value": {"text": text, "embedding": embedding,
                  "metadata": payload.get("metadata", {}), "created_at": time.time()}}})
    return {"id": mid}

def search(payload):
    q = iii.trigger({"function_id": "embed::text", "payload": {"input": [payload["query"]]}})[0]
    entries = iii.trigger({"function_id": "state::list",
                           "payload": {"scope": scope(payload["namespace"])}})
    ranked = sorted(
        ({"id": e["key"], "text": e["value"]["text"], "metadata": e["value"]["metadata"],
          "score": cosine(q, e["value"]["embedding"])} for e in entries),
        key=lambda m: m["score"], reverse=True)
    return ranked[: payload.get("k", 5)]

def forget(payload):
    iii.trigger({"function_id": "state::delete",
                 "payload": {"scope": scope(payload["namespace"]), "key": payload["id"]}})
    return {"forgotten": payload["id"]}

iii.register_function("memory::add", add)
iii.register_function("memory::search", search)
iii.register_function("memory::forget", forget)

# Capture published memory events asynchronously.
iii.register_trigger({
    "type": "durable:subscriber",
    "function_id": "memory::add",
    "config": {"topic": "memory.capture"},
})
```

## When to Use

- Use for agent long-term memory, semantic recall, context injection, and automatic memory capture
  from streams or queues on iii.
- Use the namespace argument to isolate memory per agent, user, or session.

## Boundaries

- For function/trigger registration and invocation-mode semantics, see `iii-core-primitives`.
- For full agentic pipeline designs, see `iii-architecture-patterns`.
- For the vector, state, and embedding workers this skill calls, see their worker docs and
  `workers.iii.dev`; do not redefine them here.
