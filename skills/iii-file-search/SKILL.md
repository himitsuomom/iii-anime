---
name: iii-file-search
description: >-
  Use when giving agents fuzzy file search over a workspace, content/grep search for agents,
  ranked search results to read next, or a workspace search worker backed by the fff search SDK,
  with optional index caching in iii state and RBAC-scoped search roots.
---

# File Search Worker

A `file-search` worker wraps the [`fff`](https://github.com/dmtrKovalenko/fff) search SDK (file
search optimized for AI agents, multi-language) and exposes it as native iii functions. Agents call
it **synchronously** to locate files and code, then read the top-ranked results.

| Function | Does | Payload |
| --- | --- | --- |
| `search::files` | Fuzzy path match | `{ query, limit?, root? }` |
| `search::content` | Ripgrep-style content search | `{ query, glob?, limit?, root? }` |
| `search::symbols` | Definition/symbol lookup | `{ query, kind?, limit?, root? }` |

All three return ranked results: `{ results: [{ path, score, line?, preview? }], truncated }`.
Higher `score` is a better match. Results are ordered so an agent can read the head of the list and
stop.

## Why a Worker

`fff` ranking runs in-process and is fast enough to call inline. Register it as functions so any
agent, trigger, or pipeline can `trigger({ function_id: "search::files", payload })` and get ranked
candidates back synchronously — no shelling out, no parsing CLI output.

| Mode | Use |
| --- | --- |
| Sync `trigger(...)` | Default. Agent needs ranked results immediately |
| Void | Never — the result is the point |
| Enqueue | Only for bulk re-indexing of a large root |

## Indexing and State

`fff` matches against a file list. For small roots, build it per call. For large or hot roots,
cache the index in iii state and refresh on a `state` or `cron` trigger.

| State scope | Key | Value |
| --- | --- | --- |
| `search.index` | `<root>` | `{ files: string[], builtAt }` |

Bind a `state` trigger on `search.index` to invalidate downstream caches, or a `cron` trigger to
rebuild stale indexes.

## RBAC-Scoped Roots

Never search outside an allowed root. Resolve `root` from caller identity, default to the worker's
configured base, and reject traversal. Treat the resolved root as a hard boundary before any `fff`
call.

```typescript
function resolveRoot(payload, identity) {
  const base = identity?.searchRoot ?? WORKSPACE_ROOT;
  const root = path.resolve(base, payload.root ?? ".");
  if (!root.startsWith(base)) throw new Error("search root outside RBAC scope");
  return root;
}
```

## TypeScript

```typescript
import { registerWorker } from "iii-sdk";
import { fff } from "fff";
import path from "node:path";

const WORKSPACE_ROOT = process.env.SEARCH_ROOT ?? process.cwd();
const iii = registerWorker("ws://localhost:49134", { workerName: "file-search" });

async function index(root: string): Promise<string[]> {
  const cached = await iii.trigger({
    function_id: "state::get",
    payload: { scope: "search.index", key: root },
  });
  if (cached?.files) return cached.files;
  const files = await fff.listFiles(root, { ignoreGit: true });
  await iii.trigger({
    function_id: "state::set",
    payload: { scope: "search.index", key: root, value: { files, builtAt: Date.now() } },
  });
  return files;
}

iii.registerFunction("search::files", async ({ query, limit = 20, root = "." }, ctx) => {
  const dir = resolveRoot({ root }, ctx?.identity);
  const ranked = fff.match(query, await index(dir), { limit });
  return {
    results: ranked.map((r) => ({ path: r.value, score: r.score })),
    truncated: ranked.length === limit,
  };
});

iii.registerFunction("search::content", async ({ query, glob, limit = 50, root = "." }, ctx) => {
  const dir = resolveRoot({ root }, ctx?.identity);
  const hits = await fff.searchContent(query, { root: dir, glob, limit });
  return {
    results: hits.map((h) => ({ path: h.path, line: h.line, score: h.score, preview: h.text })),
    truncated: hits.length === limit,
  };
});

iii.registerFunction("search::symbols", async ({ query, kind, limit = 20, root = "." }, ctx) => {
  const dir = resolveRoot({ root }, ctx?.identity);
  const syms = await fff.searchSymbols(query, { root: dir, kind, limit });
  return {
    results: syms.map((s) => ({ path: s.path, line: s.line, score: s.score, preview: s.name })),
    truncated: syms.length === limit,
  };
});
```

An agent then chains a search into a read:

```typescript
const { results } = await iii.trigger({
  function_id: "search::files",
  payload: { query: "order validate", limit: 5 },
});
const top = results[0]?.path; // read this next
```

## Python

```python
from iii import register_worker
from fff import list_files, match, search_content
import os, os.path

WORKSPACE_ROOT = os.environ.get("SEARCH_ROOT", os.getcwd())
iii = register_worker("ws://localhost:49134")

def resolve_root(payload, identity):
    base = (identity or {}).get("search_root", WORKSPACE_ROOT)
    root = os.path.realpath(os.path.join(base, payload.get("root", ".")))
    if not root.startswith(base):
        raise ValueError("search root outside RBAC scope")
    return root

def index(root):
    cached = iii.trigger({"function_id": "state::get",
                          "payload": {"scope": "search.index", "key": root}})
    if cached and cached.get("files"):
        return cached["files"]
    files = list_files(root, ignore_git=True)
    iii.trigger({"function_id": "state::set",
                 "payload": {"scope": "search.index", "key": root, "value": {"files": files}}})
    return files

def search_files(payload, ctx=None):
    root = resolve_root(payload, (ctx or {}).get("identity"))
    limit = payload.get("limit", 20)
    ranked = match(payload["query"], index(root), limit=limit)
    return {"results": [{"path": r.value, "score": r.score} for r in ranked],
            "truncated": len(ranked) == limit}

def search_content_fn(payload, ctx=None):
    root = resolve_root(payload, (ctx or {}).get("identity"))
    limit = payload.get("limit", 50)
    hits = search_content(payload["query"], root=root, glob=payload.get("glob"), limit=limit)
    return {"results": [{"path": h.path, "line": h.line, "score": h.score, "preview": h.text}
                        for h in hits],
            "truncated": len(hits) == limit}

iii.register_function("search::files", search_files)
iii.register_function("search::content", search_content_fn)
```

## Worker Manifest

```yaml
name: file-search
runtime:
  kind: node
  package_manager: npm
  entry: file-search.ts
scripts:
  install: "npm install iii-sdk fff"
  start: "node --experimental-strip-types file-search.ts"
```

## Boundaries

- For invocation modes, trigger binding, and worker registration mechanics, use `iii-core-primitives`.
- For RBAC listeners and identity propagation, use `iii-engine-config`.
- For chaining search into agent read/act loops, use `iii-architecture-patterns`.
