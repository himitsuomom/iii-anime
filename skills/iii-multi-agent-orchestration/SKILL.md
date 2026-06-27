---
name: iii-multi-agent-orchestration
description: >-
  Use when coordinating multiple specialized agents, building role-based agent teams
  (PM, architect, engineer, reviewer), running agent swarms with fan-out/fan-in,
  handing off work between agents, multiplexing many agent instances, or sharing a
  blackboard of state across agents in iii.
---

# Multi-Agent Orchestration

Model a multi-agent system the way a single-process AI software company would: one **role** per
iii function, **handoff** through function calls and queues, a **blackboard** in shared state, and
**swarms** through fan-out enqueue plus a fan-in aggregator. No new primitive is required. This is
the agentic backend from `iii-architecture-patterns` scaled to teams.

## Mapping Frameworks to iii

| External concept | iii shape |
| --- | --- |
| Role / agent (MetaGPT PM, architect, engineer, reviewer) | One `registerFunction` per role |
| Standard operating procedure / pipeline | Functions chained by sync `trigger` or queue handoff |
| Shared message pool / blackboard | A `state` scope keyed by run id |
| Swarm fan-out (ruflo) | N enqueues to a worker queue |
| Swarm fan-in / aggregation | Count completions in state, fire aggregator at quorum |
| Agent multiplexer (herdr) | Many worker instances registering the same function id |
| Workflow coordination | `state` and `stream` triggers reacting to blackboard writes |

## Roles as Functions

Give each role a single responsibility and a stable function id under an `agents::` namespace. A role
reads the blackboard, does its work, writes its output back, and hands off to the next role.

| Role | Function id | Reads | Writes |
| --- | --- | --- | --- |
| PM | `agents::pm` | requirement | `/prd` |
| Architect | `agents::architect` | `/prd` | `/design` |
| Engineer | `agents::engineer` | `/design` | `/code` |
| Reviewer | `agents::reviewer` | `/code` | `/review`, verdict |

## Blackboard via Shared State

Use one state scope per run as the shared message pool. Every role appends to it; no role holds the
canonical context in memory. Bind a `state` trigger to react to writes when coordination should be
event-driven instead of a fixed chain.

```typescript
import { registerWorker, TriggerAction } from "iii-sdk";

const iii = registerWorker("ws://localhost:49134", { workerName: "agent-team" });

async function post(runId: string, role: string, value: unknown) {
  await iii.trigger({
    function_id: "state::update",
    payload: { scope: "run", key: runId, ops: [{ op: "set", path: `/${role}`, value }] },
  });
}

async function read(runId: string) {
  return iii.trigger({ function_id: "state::get", payload: { scope: "run", key: runId } });
}
```

## Handoff Between Roles

Sequential handoff is a sync `trigger` when the caller needs the result, or an `Enqueue` when the
next role should run durably and independently. Chain the SOP role by role.

```typescript
iii.registerFunction("agents::pm", async ({ runId, requirement }) => {
  const prd = await llm(`Write a PRD for: ${requirement}`);
  await post(runId, "prd", prd);
  return iii.trigger({
    function_id: "agents::architect",
    payload: { runId },
    action: TriggerAction.Enqueue({ queue: "agent-sop" }),
  });
});

iii.registerFunction("agents::architect", async ({ runId }) => {
  const { prd } = await read(runId);
  const design = await llm(`Design a system for this PRD: ${prd}`);
  await post(runId, "design", design);
  return iii.trigger({
    function_id: "agents::engineer",
    payload: { runId },
    action: TriggerAction.Enqueue({ queue: "agent-sop" }),
  });
});
```

The reviewer can loop back: if its verdict is `reject`, re-enqueue `agents::engineer` with the review
notes on the blackboard. Cap iterations with a counter in state to avoid infinite review cycles.

## Swarms: Fan-Out and Fan-In

A swarm runs the same role over many inputs in parallel, then aggregates. Fan-out is N enqueues to a
worker queue; the queue's concurrency policy controls parallelism. Fan-in counts completions in state
and fires the aggregator at quorum.

```typescript
iii.registerFunction("swarm::dispatch", async ({ runId, tasks }) => {
  await iii.trigger({
    function_id: "state::set",
    payload: { scope: "swarm", key: runId, value: { total: tasks.length, done: 0, results: {} } },
  });
  for (const task of tasks) {
    await iii.trigger({
      function_id: "swarm::worker",
      payload: { runId, task },
      action: TriggerAction.Enqueue({ queue: "swarm-tasks" }),
    });
  }
  return { dispatched: tasks.length };
});

iii.registerFunction("swarm::worker", async ({ runId, task }) => {
  const result = await llm(`Solve: ${task.prompt}`);
  await iii.trigger({
    function_id: "state::update",
    payload: {
      scope: "swarm",
      key: runId,
      ops: [
        { op: "set", path: `/results/${task.id}`, value: result },
        { op: "increment", path: "/done", value: 1 },
      ],
    },
  });
  return { id: task.id };
});

iii.registerFunction("swarm::on-progress", async (event) => {
  const { total, done, results } = event.new_value;
  if (done < total) return;
  await iii.trigger({ function_id: "swarm::aggregate", payload: { runId: event.key, results } });
});

iii.registerTrigger({
  type: "state",
  function_id: "swarm::on-progress",
  config: { scope: "swarm" },
});
```

The `state` trigger turns fan-in into a reactive quorum check: the aggregator fires exactly once,
when the final worker brings `done` up to `total`. No polling, no central wait loop.

## Multiplexing Instances

To multiplex many instances of a role (herdr-style), start multiple workers that each register the
same function id. The engine load-balances enqueued work across them; scaling out is starting another
worker process. Tag each with worker metadata for discovery via `engine::workers::list`.

```python
from iii import register_worker

iii = register_worker("ws://localhost:49134")

def worker(payload):
    run_id, task = payload["runId"], payload["task"]
    result = llm(f"Solve: {task['prompt']}")
    iii.trigger({
        "function_id": "state::update",
        "payload": {
            "scope": "swarm",
            "key": run_id,
            "ops": [
                {"op": "set", "path": f"/results/{task['id']}", "value": result},
                {"op": "increment", "path": "/done", "value": 1},
            ],
        },
    })
    return {"id": task["id"]}

# Run this file on N hosts/processes; all register the same id and share the queue.
iii.register_function("swarm::worker", worker)
```

## Selection Rules

- Use sync `trigger` for handoff when the calling role needs the next role's output inline.
- Use `Enqueue` for handoff when roles must run durably, retry on failure, or run on another worker.
- Use a single `state` scope per run as the blackboard; key it by run id, never global mutable memory.
- Use a `state` trigger for fan-in quorum and for any event-driven role activation.
- Use named queue concurrency, not application code, to bound swarm parallelism.
- Cap review/critique loops with an iteration counter in state.

## When to Use

- Use this skill for role-based agent teams, swarms, fan-out/fan-in, agent handoff, shared
  blackboards, and multiplexing agent instances on iii.

## Boundaries

- For function registration, trigger config, invocation modes, and worker creation, use
  `iii-core-primitives`.
- For the general agentic backend, workflows, and CQRS, use `iii-architecture-patterns`.
- For queue retry, FIFO, and concurrency policy, use `iii-engine-config`.
- For failed handoffs, timeouts, and retryability, use `iii-error-handling`.
