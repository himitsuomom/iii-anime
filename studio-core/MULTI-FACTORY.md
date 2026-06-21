# Multi-factory on iii — integrating your Claude assets & going to production

This is the shared core and the production playbook for running **multiple AI
factories on one iii engine** (e.g. [`app-studio`](../app-studio) for software,
[`video-studio`](../video-studio) for video), and for plugging in the **tools,
skills, MCP servers, and plugins you already built with Claude**.

---

## Part 1 — Can my existing Claude assets be integrated? Yes.

The factory brains and build backends drive your **local Claude Code** (`claude
-p`) using your existing login. So anything that login already has works, and
the rest is injected per job via flags. Set these once as env on the engine
process; every factory agent picks them up (`studio-core/src/assets.ts`):

| Your asset | How it's used | Env var → CLI flag |
|---|---|---|
| **Skills** | Auto-resolve from your Claude Code user settings (no setup). Project skills via a dir. | `STUDIO_ADD_DIRS` → `--add-dir` |
| **MCP servers** | The agent can call your MCP tools | `STUDIO_MCP_CONFIG` → `--mcp-config`; pre-approve with `STUDIO_EXTRA_TOOLS=mcp__yourserver` |
| **Plugins** (slash commands / hooks / subagents) | Loaded for the session | `STUDIO_PLUGIN_DIRS` → `--plugin-dir`, `STUDIO_PLUGIN_URLS` → `--plugin-url` |
| **Custom subagents** | Available to delegate to | `STUDIO_AGENTS_JSON` → `--agents` |
| **Settings** (CLAUDE.md, permissions) | Applied | `STUDIO_CLAUDE_SETTINGS` → `--settings` |
| **Model / fallback** | Per-deployment override | `STUDIO_MODEL` → `--model`, `STUDIO_FALLBACK_MODEL` → `--fallback-model` |
| **iii functions/workers you built** | Call directly from any handler | `iii.trigger({ function_id, payload })` |

Example (one factory, with your MCP + skills + a plugin):

```bash
STUDIO_MCP_CONFIG=$HOME/.claude/mcp.json \
STUDIO_ADD_DIRS=$HOME/my-skills \
STUDIO_PLUGIN_DIRS=$HOME/my-plugins/reviewer \
STUDIO_EXTRA_TOOLS="mcp__github,mcp__linear" \
iii --config studio-core/deploy/multi-factory.local.yml
```

Now the build agent that implements each app can use your GitHub/Linear MCP
tools, your skills, and your reviewer plugin — no code change. (On the
`api` build backend, the equivalent is the MCP connector + Agent Skills API;
that wiring is a follow-up.)

---

## Part 2 — Production multi-factory infrastructure

**One engine, many factories, namespaced so they never collide.** Each factory
declares a `FactoryDescriptor` (`studio-core/src/factory.ts`): a unique HTTP
route prefix, iii state scope, and heavy-stage queue. The registry rejects
prefix/scope collisions at startup.

```
                ┌──────────── one iii engine ────────────┐
 POST /projects │ app-studio   scope "studio"  q studio-build │
 POST /video/*  │ video-studio scope "video"   q video-render │
                │ shared: state · queue · pubsub · traces · HTTP · Vault │
                └──────────── studio-core (shared) ──────────┘
```

`studio-core` owns the cross-factory code. Today: **asset integration**, the
**factory registry**, **auth + secrets**, and the **execution sandbox**
(`src/sandbox` — exec/edit/workspace/allowlist + the `unshare` runner; both
factories import it from here). The store, wiki, and brain still live in
app-studio because they are typed against the software domain (`ProjectState` /
`Spec` / `Plan`); moving them cleanly needs a generification pass (parameterize
the state type) — that's the remaining extraction step.

Deployment config: [`deploy/multi-factory.local.yml`](./deploy/multi-factory.local.yml)
runs one engine with state/http/pubsub/queue and starts the factory worker(s).
Add a factory by adding its `iii-exec` line and its `FactoryDescriptor`.

---

## Production readiness checklist

**Done**
- Pipeline (intake→design→build→qa→approval→deliver) with the build↔qa loop.
- Sandbox: allowlist + workdir confinement + timeout, **plus optional `unshare`
  kernel-namespace isolation** (`STUDIO_SANDBOX_ISOLATION=unshare`).
- Human **approval gate**, **idempotency** + cron **resume/sweep**.
- **LLM wiki** (auto-doc) + knowledge reuse into builds.
- **Dashboard** (`/`) and **Console SPA panel** (`/studio`).
- **Asset integration** (skills/MCP/plugins/subagents) + **namespacing** primitives.
- App-type **adapters**; second factory (**video-studio**) skeleton.

**Required before real production**
- [ ] **Auth** on the HTTP routes — they are currently open. Put the engine
      behind an auth gateway or add an auth trigger; never expose `/projects`
      and `/wiki/ask` unauthenticated on a public network.
- [ ] **Secrets via iii Vault** — git push tokens, third-party API keys. Never
      in env that the sandbox can read, never in prompts/wiki.
- [ ] **Durable adapters** — move `iii-state`/`iii-queue` from file-based KV to
      redis/rabbitmq (or managed equivalents); back them up.
- [ ] **Cost & concurrency controls** — per-factory queue concurrency, project
      `max_iterations` caps, Task Budgets, and Claude rate-limit handling.
- [ ] **Observability/alerting** — dashboards on iii traces + per-project token
      usage/cost; alert on stuck projects and refusal spikes.
- [ ] **Stronger isolation for untrusted code** — `unshare` is on by opt-in; for
      hostile inputs consider a per-job MicroVM/rootfs (the engine's
      self-hosted sandbox path) rather than namespaces alone.
- [x] **studio-core physical extraction (sandbox)** — `src/sandbox` now lives in
      studio-core; both factories import it from here.
- [ ] **studio-core extraction (store/wiki/brain)** — generify over the state
      type first (these are typed against `ProjectState`/`Spec`/`Plan`), then move.
- [ ] **CI** — run the `app-studio`, `studio-core`, and `video-studio` test
      suites on every change.
- [ ] **HA** — multiple worker replicas; a single leader for the sweep cron to
      avoid duplicate resumes.

> The factory descriptors already prevent namespace collisions, and the
> approval gate + isolation + idempotency give a safe operational baseline. The
> items above are what turn the working system into a hardened production
> service.
