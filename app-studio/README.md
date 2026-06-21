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

# dashboard UI — submit ideas, watch the pipeline, approve/reject, browse/ask the wiki
open http://localhost:3111/            # single-file UI (ui/dashboard.html), also at /ui

# approval gate (when a project was created with require_approval)
curl -XPOST localhost:3111/projects/prj_.../approve
curl -XPOST localhost:3111/projects/prj_.../reject

# LLM wiki — every delivered app is auto-documented; ask questions across them
curl localhost:3111/wiki                 # list wiki pages
curl localhost:3111/wiki/app-...         # one page (markdown)
curl -XPOST localhost:3111/wiki/ask -H 'content-type: application/json' \
  -d '{"question":"which apps expose a /health endpoint?"}'
```

### Approval gate

Create a project with `{"idea":"...","require_approval":true}` (or set
`STUDIO_REQUIRE_APPROVAL=true`). After QA passes it pauses at
`awaiting_approval` until `POST /projects/:id/approve` (→ deliver) or `/reject`
(→ failed).

### LLM wiki

When a project is delivered, the studio asks the LLM to write a Markdown wiki
page documenting the app (overview / features / how it works / run / files) and
stores it. `POST /wiki/ask` answers natural-language questions grounded only in
those pages, citing the page slugs it used.

### Verified live (P0 + P1)

A static-web idea ran end-to-end on the engine (no API key): design picked the
`static-web` adapter, QA passed (`test -f index.html` + `node --test`), the app
was delivered, a wiki page was auto-generated, and `POST /wiki/ask` answered
from it citing `[app-...]`.

### Build backend (pluggable brain)

| `STUDIO_BUILD_BACKEND` | Backend | Auth |
|---|---|---|
| `claude-code` (default) | local `claude -p` | host's Claude Code login — no API key |
| `api` | Anthropic Messages API + our tool-use loop + our sandbox | `ANTHROPIC_API_KEY` (install `@anthropic-ai/sdk`) |

### App types (adapters)

`web-node` (zero-dependency Node, the P0 default) and `static-web` (HTML/CSS/JS).
Add a type by dropping an adapter in `src/adapters/` and calling `register()`.

### LLM wiki

Every delivered app is auto-documented into a wiki page. Browse and query it:

```
curl localhost:3111/wiki                      # list pages
curl localhost:3111/wiki/app-...              # one page (markdown)
curl -XPOST localhost:3111/wiki/ask -H 'content-type: application/json' \
  -d '{"question":"which apps expose a /health route?"}'   # grounded LLM answer
```

The wiki feeds back into builds: before implementing, the studio injects the
most relevant prior app docs into the build prompt so patterns get reused.

### Other knobs

- `require_approval` (POST body) or `STUDIO_REQUIRE_APPROVAL=true`: pause after
  QA at `awaiting_approval` until `POST /projects/:id/approve` (or `/reject`).
- `idempotency_key` (POST body): a duplicate submission maps to the same project.
- A 1-minute cron sweep resumes any stuck, non-terminal project.
- `STUDIO_API_TOKEN`: when set, the data routes (`/projects*`, `/wiki*`) require
  `Authorization: Bearer <token>` (or `x-api-key`). Unset = open (dev). The
  dashboard page itself stays public; its API calls need the token.
- `STUDIO_SECRET_<NAME>`: host-side secrets (e.g. a git push token) read via
  `EnvSecretStore`; never injected into the sandbox env. See
  [studio-core/MULTI-FACTORY.md](../studio-core/MULTI-FACTORY.md).
- `STUDIO_SANDBOX_ISOLATION=unshare`: run sandbox commands in kernel namespaces
  (mount/uts/ipc/pid + unprivileged user-ns + no network) instead of the default
  direct spawn. Falls back to direct if `unshare` is unavailable. Set
  `STUDIO_SANDBOX_NET=1` to allow network inside the isolated namespace.

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
