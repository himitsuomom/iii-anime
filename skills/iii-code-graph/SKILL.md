---
name: iii-code-graph
description: >-
  Use when indexing a codebase into a symbol/dependency knowledge graph, querying symbols, callers,
  callees, and neighbors, auto-syncing the graph on commit or file change, or grounding agents in
  code structure across TypeScript and Python.
---

# Code Graph

A `codegraph` worker indexes a repository into a symbol and dependency knowledge graph, keeps it in
sync as the code changes, and exposes graph queries as sync functions agents call for grounded code
context. It folds two patterns into native iii primitives: a pre-indexed code knowledge graph with
auto-sync, and interactive graph exploration for code understanding.

The graph lives in iii **state**. Indexing and queries are **functions**. Auto-sync is a **custom
trigger** that fires on git commit or file change.

## Graph Model

| Node kind | Fields |
| --- | --- |
| `symbol` | `id`, `name`, `kind` (function/class/method/var), `file`, `line`, `signature` |
| `file` | `id`, `path`, `hash`, `lang` |
| Edge kind | Meaning |
| `defines` | file → symbol it declares |
| `calls` | symbol → symbol it invokes |
| `imports` | file → file it depends on |
| `references` | symbol → symbol it names |

Store nodes and edges under a `codegraph` state scope keyed by repo. Key symbols by stable
`file::name` so incremental re-index can replace a file's slice without touching the rest.

## Functions

| Function | Action |
| --- | --- |
| `codegraph::index` | Full parse of the repo, write all nodes/edges to state |
| `codegraph::sync` | Incremental re-index of changed files only |
| `codegraph::query` | Find a symbol, its callers, callees, or neighbors — sync, agent-callable |
| `codegraph::explain` | Walk the graph around a symbol and return a grounded summary |

`codegraph::query` is the grounding entrypoint: agents call it `Sync` to pull exact code structure
instead of guessing. Keep it side-effect free.

## Auto-Sync Trigger

Register a custom trigger type that watches the working tree (post-commit hook or file watcher) and
calls `codegraph::sync` with the changed paths. Set up the watcher in `registerTrigger` and tear it
down in `unregisterTrigger`.

## TypeScript

```typescript
import { registerWorker, TriggerAction } from "iii-sdk";
import { parseFile, walkRepo, diffPaths } from "./graph";

const iii = registerWorker("ws://localhost:49134", { workerName: "codegraph-worker" });

const scope = (repo: string) => `codegraph:${repo}`;

iii.registerFunction("codegraph::index", async ({ repo, root }) => {
  const nodes = [], edges = [];
  for (const file of await walkRepo(root)) {
    const { symbols, calls, imports } = await parseFile(file);
    nodes.push(...symbols);
    edges.push(...calls, ...imports);
  }
  await iii.trigger({
    function_id: "state::set",
    payload: { scope: scope(repo), key: "graph", value: { nodes, edges } },
  });
  return { repo, symbols: nodes.length, edges: edges.length };
});

iii.registerFunction("codegraph::sync", async ({ repo, root, changed }) => {
  const { value: graph } = await iii.trigger({
    function_id: "state::get",
    payload: { scope: scope(repo), key: "graph" },
  });
  const kept = graph.nodes.filter((n) => !changed.includes(n.file));
  const keptEdges = graph.edges.filter((e) => !changed.includes(e.file));
  for (const file of changed) {
    const { symbols, calls, imports } = await parseFile(`${root}/${file}`);
    kept.push(...symbols);
    keptEdges.push(...calls, ...imports);
  }
  await iii.trigger({
    function_id: "state::set",
    payload: { scope: scope(repo), key: "graph", value: { nodes: kept, edges: keptEdges } },
  });
  return { repo, resynced: changed.length };
});

// Sync, agent-callable: grounded code context
iii.registerFunction("codegraph::query", async ({ repo, name, edge }) => {
  const { value: graph } = await iii.trigger({
    function_id: "state::get",
    payload: { scope: scope(repo), key: "graph" },
  });
  const node = graph.nodes.find((n) => n.name === name);
  if (!node) return { found: false };
  const callers = graph.edges.filter((e) => e.kind === "calls" && e.to === node.id);
  const callees = graph.edges.filter((e) => e.kind === "calls" && e.from === node.id);
  return { found: true, node, callers, callees };
});

// Custom trigger: re-index on commit / file change
iii.registerTriggerType(
  { id: "git-commit", description: "Fires codegraph::sync on each commit with changed paths" },
  {
    registerTrigger: async (ctx, config) => {
      const watcher = watchGit(config.root, async (commit) => {
        await ctx.trigger({
          function_id: config.function_id,
          payload: { repo: config.repo, root: config.root, changed: diffPaths(commit) },
          action: TriggerAction.Void(),
        });
      });
      return { watcher };
    },
    unregisterTrigger: async (_ctx, _config, state) => state.watcher.close(),
  },
);

iii.registerTrigger({
  type: "git-commit",
  function_id: "codegraph::sync",
  config: { repo: "iii-anime", root: "/home/user/iii-anime" },
});
```

## Python

```python
from iii import register_worker
from graph import parse_file, walk_repo

iii = register_worker("ws://localhost:49134")

def scope(repo): return f"codegraph:{repo}"

def index(req):
    nodes, edges = [], []
    for file in walk_repo(req["root"]):
        sym, calls, imports = parse_file(file)
        nodes += sym
        edges += calls + imports
    iii.trigger({"function_id": "state::set",
                 "payload": {"scope": scope(req["repo"]), "key": "graph",
                             "value": {"nodes": nodes, "edges": edges}}})
    return {"repo": req["repo"], "symbols": len(nodes), "edges": len(edges)}

def query(req):
    graph = iii.trigger({"function_id": "state::get",
                         "payload": {"scope": scope(req["repo"]), "key": "graph"}})["value"]
    node = next((n for n in graph["nodes"] if n["name"] == req["name"]), None)
    if not node:
        return {"found": False}
    callers = [e for e in graph["edges"] if e["kind"] == "calls" and e["to"] == node["id"]]
    callees = [e for e in graph["edges"] if e["kind"] == "calls" and e["from"] == node["id"]]
    return {"found": True, "node": node, "callers": callers, "callees": callees}

iii.register_function("codegraph::index", index)
iii.register_function("codegraph::query", query)
```

## Grounding Agents

An agent function calls `codegraph::query` with `Sync` before reasoning so its answer cites real
symbols and edges instead of hallucinated ones:

```typescript
const ctx = await iii.trigger({
  function_id: "codegraph::query",
  payload: { repo: "iii-anime", name: "renderFrame", edge: "callers" },
});
// feed ctx.callers / ctx.callees into the agent prompt as grounded context
```

## Boundaries

- For the function/trigger/worker model, custom trigger lifecycle, and state-trigger payloads, use
  `iii-core-primitives`.
- For state worker setup and the `state::get` / `state::set` capability, use the state worker docs.
- For agentic pipelines that consume `codegraph::query`, use `iii-architecture-patterns`.
- Parser and language-detection internals belong in the worker code, not in a top-level iii skill.
