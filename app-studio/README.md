# app-studio

A virtual app-studio orchestrated on iii: feed it an idea, and a pipeline of
roles (intake → design → build → QA → deliver) produces a tested app. The build
"brain" is pluggable and defaults to the local **Claude Code** CLI, so it runs
with your existing Claude Code login — no `ANTHROPIC_API_KEY` wiring. See the
design docs in this folder ([DESIGN.md](./DESIGN.md), [P0-DETAIL.md](./P0-DETAIL.md),
[BUILD-BACKENDS.md](./BUILD-BACKENDS.md)).

## Status (P0)

| Piece | State |
|---|---|
| sandbox (`exec`/`edit`, workdir confinement, allowlist, timeout) | ✅ implemented + unit tested |
| state machine (`decide`, idempotency, build↔qa loop) | ✅ implemented + unit tested |
| pipeline handlers (intake/design/build/qa/deliver) | ✅ implemented |
| orchestrator apply layer | ✅ implemented + e2e tested with fakes |
| Claude Code build backend (`claude -p`) | ✅ implemented + proven (no API key) |
| iii wiring (`index.ts`, `iii-store.ts`, `local.yml`) | ✅ implemented |
| **live end-to-end on the real engine** | ✅ **verified** (see below) |

### Verified live run (P0)

Built the engine (`cargo build --bin iii`), started it with `local.yml`, and
posted an idea — **with `ANTHROPIC_API_KEY` unset** (the worker's brain + build
backend used the host's Claude Code login):

```
POST /projects {"idea":"a tiny HTTP server with a GET /health route ..."}
  -> { "project_id": "prj_mqn73z5y316sd1" }
```

The pipeline ran intake → design → build → qa → deliver and reached
`status: "delivered"` on the first iteration (`last_qa.passed: true`,
`score: 100`). It generated a zero-dependency Node app — `server.js`
(`node:http`, `GET /health` → `{"status":"ok"}`) and `test.js` — and QA's
`node --test` passed. Independently re-running `node --test` in the workdir: 4/4
pass. P0 biases intake/design to zero-dependency Node (stdlib only, `node --test`)
so the loop is fast and offline; lift that in P1 via app-type adapters.

## Tests (no engine, no API key)

```bash
cd app-studio
pnpm exec tsx --test "src/**/*.test.ts"     # 34 tests: sandbox + machine + full pipeline (fakes + real sandbox)
```

Opt-in real end-to-end against the local Claude Code CLI (uses your Claude Code
login; spends tokens):

```bash
STUDIO_E2E=1 pnpm exec tsx --test src/build/claude-code-backend.test.ts
```

## Run the worker (live)

Needs `iii-sdk` installed and an iii engine. The brain/backend use the local
`claude` CLI, so make sure Claude Code is logged in on the host.

```bash
cd app-studio && npm install      # installs iii-sdk, tsx, typescript
# from the repo root, start the engine with the studio config:
iii --config app-studio/local.yml
# then:
curl -XPOST localhost:3111/projects -H 'content-type: application/json' \
  -d '{"idea":"a web page with a click counter"}'
# -> { "project_id": "prj_..." }  (pipeline runs in the background)

curl localhost:3111/projects/prj_...    # full project state (status, plan, last_qa, artifacts)
curl localhost:3111/projects            # list all projects (summary)
```

### Build backend (pluggable brain)

| `STUDIO_BUILD_BACKEND` | Backend | Auth |
|---|---|---|
| `claude-code` (default) | local `claude -p` | host's Claude Code login — no API key |
| `api` | Anthropic Messages API + our tool-use loop + our sandbox | `ANTHROPIC_API_KEY` (install `@anthropic-ai/sdk`) |

### App types (adapters)

`web-node` (zero-dependency Node, the P0 default) and `static-web` (HTML/CSS/JS).
Add a type by dropping an adapter in `src/adapters/` and calling `register()`.

## Layout

```
src/
  sandbox/     exec/edit/workspace/allowlist  — the case-A execution boundary
  orchestrator/ machine.ts (pure decide) + apply.ts (drives the pipeline)
  pipeline/    handlers.ts — one handler per stage
  brain/       Brain interface + ClaudeCliBrain (claude -p, structured output)
  build/       BuildBackend interface + ClaudeCodeBackend (claude -p)
  runtime/     Store interface + MemoryStore (tests) + IiiStore (live)
  types.ts     ProjectState / Spec / Plan / Rubric / QaResult / Artifacts
  index.ts     iii worker entrypoint (HTTP intake + sandbox + orchestrator)
```

## Configuration

| Env | Default | Meaning |
|---|---|---|
| `STUDIO_WORK_ROOT` | `<tmp>/iii-studio-work` | base dir for per-project workdirs |
| `STUDIO_BUILD_MAX_TURNS` | `60` | hard cap on build-agent turns per attempt |
| `STUDIO_HTTP_PORT` | `3111` | HTTP intake port (local.yml) |
| `III_URL` | `ws://localhost:49134` | engine websocket |
