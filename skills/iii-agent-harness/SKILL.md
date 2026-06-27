---
name: iii-agent-harness
description: >-
  Use when running a plan-work-review agent loop on iii, modeling a gated task state machine in iii
  state, firing automatic review as a trigger on work completion, iterating on failed review with
  retries, and compounding reusable skills and context across runs.
---

# Agent Harness

A coding-agent harness is a disciplined `plan -> work -> review` cycle with gated state transitions.
Run it natively on iii: each phase is a `Function`, transitions are tracked in `state`, review fires
automatically from a `state` trigger, and failed review re-enqueues `work`. Every run can write back
to reusable skills and context, so the harness improves itself ("compound engineering").

## Phase Map

| Phase | Function | Reads | Writes | Hands off to |
| --- | --- | --- | --- |
| Plan | `harness::plan` | task spec | `plan`, sets `phase=working` | `harness::work` (enqueue) |
| Work | `harness::work` | `plan` | `diff`, sets `phase=reviewing` | review (state trigger) |
| Review | `harness::review` | `diff`, `plan` | `verdict`, sets `phase=done`/`failed` | `harness::iterate` on fail |
| Iterate | `harness::iterate` | `verdict`, `attempts` | bumps `attempts`, `phase=working` | `harness::work` (enqueue) |

## Task State Machine

Hold one document per task in state scope `harness`, keyed by `taskId`. `phase` is the gate; only the
owning phase function advances it. The `state` trigger on `phase` reaching `reviewing` runs review
automatically, so work never calls review directly.

| `phase` | Meaning | Next |
| --- | --- | --- |
| `planning` | plan in progress | `working` |
| `working` | implementation in progress | `reviewing` |
| `reviewing` | automatic review running | `done` or `failed` |
| `failed` | review rejected, under retry budget | `working` |
| `done` / `abandoned` | terminal (passed, or retries exhausted) | — |

```typescript
import { registerWorker, TriggerAction } from "iii-sdk";

const iii = registerWorker("ws://localhost:49134", { workerName: "harness" });
const MAX_ATTEMPTS = 3;

async function setPhase(taskId: string, phase: string, patch: Record<string, unknown> = {}) {
  await iii.trigger({
    function_id: "state::update",
    payload: {
      scope: "harness",
      key: taskId,
      ops: [
        { op: "set", path: "/phase", value: phase },
        ...Object.entries(patch).map(([k, v]) => ({ op: "set", path: `/${k}`, value: v })),
      ],
    },
  });
}
```

## Plan and Work

`plan` decomposes the spec, then enqueues `work` so the implementation runs on a retryable queue.

```typescript
iii.registerFunction("harness::plan", async (task) => {
  const plan = await iii.trigger({ function_id: "llm::plan", payload: task });
  await setPhase(task.id, "working", { plan, attempts: 0 });
  await iii.trigger({
    function_id: "harness::work",
    payload: { id: task.id },
    action: TriggerAction.Enqueue({ queue: "harness-work" }),
  });
  return { id: task.id, phase: "working" };
});

iii.registerFunction("harness::work", async ({ id }) => {
  const task = await iii.trigger({ function_id: "state::get", payload: { scope: "harness", key: id } });
  const diff = await iii.trigger({ function_id: "llm::implement", payload: task.plan });
  // setting phase=reviewing is the gate that fires the review trigger
  await setPhase(id, "reviewing", { diff });
  return { id, phase: "reviewing" };
});
```

## Automatic Review

Bind a `state` trigger so review runs the instant `work` writes `phase=reviewing`. Use a condition
function so the trigger fires only on that transition, not on every write to the document.

```typescript
iii.registerFunction("harness::reviewing?", (event) => event.new_value?.phase === "reviewing");

iii.registerFunction("harness::review", async (event) => {
  const { key: id, new_value: task } = event;
  const verdict = await iii.trigger({ function_id: "llm::review", payload: { plan: task.plan, diff: task.diff } });
  if (verdict.pass) {
    await setPhase(id, "done", { verdict });
    await iii.trigger({ function_id: "harness::compound", payload: { id, verdict }, action: TriggerAction.Void() });
    return { id, phase: "done" };
  }
  await setPhase(id, "failed", { verdict });
  await iii.trigger({ function_id: "harness::iterate", payload: { id } });
  return { id, phase: "failed" };
});

iii.registerTrigger({
  type: "state",
  function_id: "harness::review",
  config: { scope: "harness", condition_function_id: "harness::reviewing?" },
});
```

## Iteration on Failed Review

`iterate` enforces the retry budget. Under budget it re-enqueues `work` with the review feedback in
state; over budget it parks the task as `abandoned` so the loop terminates instead of spinning.

```typescript
iii.registerFunction("harness::iterate", async ({ id }) => {
  const task = await iii.trigger({ function_id: "state::get", payload: { scope: "harness", key: id } });
  const attempts = (task.attempts ?? 0) + 1;
  if (attempts >= MAX_ATTEMPTS) {
    await setPhase(id, "abandoned", { attempts });
    return { id, phase: "abandoned" };
  }
  await setPhase(id, "working", { attempts, feedback: task.verdict?.notes });
  await iii.trigger({
    function_id: "harness::work",
    payload: { id },
    action: TriggerAction.Enqueue({ queue: "harness-work" }),
  });
  return { id, phase: "working", attempts };
});
```

### Python loop entry

```python
from iii import register_worker

iii = register_worker("ws://localhost:49134")

def plan(task):
    spec = iii.trigger({"function_id": "llm::plan", "payload": task})
    iii.trigger({"function_id": "state::update", "payload": {
        "scope": "harness", "key": task["id"],
        "ops": [{"op": "set", "path": "/phase", "value": "working"},
                {"op": "set", "path": "/plan", "value": spec},
                {"op": "set", "path": "/attempts", "value": 0}],
    }})
    iii.trigger({"function_id": "harness::work", "payload": {"id": task["id"]},
                 "action": {"type": "enqueue", "queue": "harness-work"}})
    return {"id": task["id"], "phase": "working"}

iii.register_function("harness::plan", plan)
```

## Compound Engineering

On a pass, `harness::compound` distills what worked into reusable context: append the accepted plan
and review notes to a long-lived `knowledge` state scope, and update function/trigger `metadata` that
generated skills read. Future `plan` runs load that context, so each cycle raises the floor.

```typescript
iii.registerFunction("harness::compound", async ({ id, verdict }) => {
  await iii.trigger({
    function_id: "state::update",
    payload: { scope: "knowledge", key: "review-lessons",
      ops: [{ op: "append", path: "/lessons", value: { id, learned: verdict.notes } }] },
  });
});
```

Feed `knowledge::review-lessons` into the `llm::plan` and `llm::review` prompts so accumulated
lessons constrain future runs. Keep secrets out of `metadata` and the knowledge scope.

## Observability

The state document is the loop's audit log: `phase`, `attempts`, `plan`, `diff`, and `verdict` are
all queryable. For live dashboards or alerting, bind a second `state` trigger on scope `harness` that
forwards transitions to a stream or log, and read `engine::functions::list` /
`engine::triggers::list` to confirm every phase function and the review trigger are registered.

| Want | Use |
| --- | --- |
| Current phase / attempt of a task | `state::get` on `harness/<taskId>` |
| Live transition feed | `state` trigger -> `stream::send` (void) |
| Stuck tasks (retries exhausted) | query `harness` docs where `phase=abandoned` |
| Loop wiring is registered | `engine::triggers::list`, `engine::functions::list` |

## Boundaries

- For trigger config, `condition_function_id`, invocation modes, and function registration, use
  `iii-core-primitives`.
- For queue retry, FIFO, and concurrency policy on `harness-work`, use `iii-engine-config`.
- For broader agentic handoff patterns beyond this loop, use `iii-architecture-patterns`.
- For failed invocations, timeouts, and retryability, use `iii-error-handling`.
