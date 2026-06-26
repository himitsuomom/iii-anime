# iii-understand

An iii **worker** that serves a codebase **knowledge graph** as functions and
HTTP triggers.

It reads the `knowledge-graph.json` produced by the
[Understand-Anything](https://github.com/Egonex-AI/Understand-Anything)
`/understand` skill and exposes it through the engine, so any other worker — or
an agent — can query a project's structure (search, neighbors, call paths,
deep-dive explanations, onboarding tour) instead of re-reading files.

```
/understand  ─writes─▶  .understand-anything/knowledge-graph.json  ─served by─▶  iii-understand worker
```

## Functions

| Function ID             | Input                                              | Returns |
| ----------------------- | -------------------------------------------------- | ------- |
| `understand::status`    | —                                                  | Whether a graph exists + project meta + counts |
| `understand::overview`  | —                                                  | Project meta, node-type breakdown, layers |
| `understand::search`    | `{ query, type?, layer?, limit? }`                 | Ranked node hits |
| `understand::node`      | `{ id }`                                            | Node + layers + incoming/outgoing edges |
| `understand::neighbors` | `{ id, direction?: in\|out\|both, edgeType? }`     | Connected nodes |
| `understand::explain`   | `{ id?, file? }`                                   | Node summary + dependsOn / usedBy |
| `understand::tour`      | —                                                  | Dependency-ordered tour steps |

## HTTP surface (read-only)

| Method & path                       | Maps to |
| ----------------------------------- | ------- |
| `GET /understand/status`            | `understand::status` |
| `GET /understand/overview`          | `understand::overview` |
| `GET /understand/search?q=&type=&layer=&limit=` | `understand::search` |
| `GET /understand/node/:id`          | `understand::node` |
| `GET /understand/explain?file=` / `/understand/explain/:id` | `understand::explain` |
| `GET /understand/tour`              | `understand::tour` |

## Configuration

| Env var                 | Default                                              | Purpose |
| ----------------------- | ---------------------------------------------------- | ------- |
| `III_URL`               | `ws://localhost:49134`                               | Engine WebSocket URL |
| `UNDERSTAND_GRAPH_PATH` | —                                                    | Explicit path to `knowledge-graph.json` |
| `UNDERSTAND_REPO_ROOT`  | process cwd                                           | Repo whose `.understand-anything/knowledge-graph.json` to serve |

The graph is cached in memory and invalidated by file mtime, so re-running
`/understand` is picked up automatically on the next query.

## Run

```bash
# 1. Generate a graph in the target repo (Understand-Anything /understand skill)
#    -> writes .understand-anything/knowledge-graph.json
# 2. Start the engine with the bundled config, then:
pnpm --filter @iii-hq/iii-understand dev
```

## Test

```bash
pnpm --filter @iii-hq/iii-understand test
```

Tests exercise the pure query module against `fixtures/sample-knowledge-graph.json`
and require neither the engine nor a real graph.
