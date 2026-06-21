# @iii/studio-core

Shared core for iii AI factories. Hosts the cross-factory code so multiple
factories (e.g. [`app-studio`](../app-studio), [`video-studio`](../video-studio))
run on one engine and reuse the same mechanism.

- `src/assets.ts` — integrate your existing Claude assets (skills/MCP/plugins/
  subagents/settings/model) into factory agents. `assetArgs()` builds the CLI
  flags; `assetsFromEnv()` reads a default bundle from env.
- `src/factory.ts` — `FactoryDescriptor` + registry: per-factory namespacing
  (route prefix / state scope / queue) with collision checks.
- `src/auth.ts` — HTTP auth gate (`STUDIO_API_TOKEN`); `src/secrets.ts` —
  host-side secrets that never reach the sandbox.
- `src/sandbox/` — the execution boundary (exec/edit/workspace/allowlist + the
  `unshare` isolation runner), shared by every factory.
- `src/store.ts` (generic `KvStore<T>`), `src/idempotency.ts`, `src/brain.ts` +
  `src/claude-cli-brain.ts`, `src/wiki/` (store/retrieval/iii-store + generic
  `generateWikiPage`), `src/leader.ts` (HA), `src/alerts.ts` — the shared mechanism.

See **[MULTI-FACTORY.md](./MULTI-FACTORY.md)** for the integration guide,
production deployment, and the readiness checklist, and
[`deploy/multi-factory.local.yml`](./deploy/multi-factory.local.yml) for a
one-engine, multi-factory config.

```bash
cd studio-core && pnpm exec tsx --test "src/**/*.test.ts"   # 32 tests (assets, factory, auth, secrets, sandbox, runner)
```

> Roadmap: the sandbox now lives here. The store, wiki, and brain remain in
> app-studio because they're typed against the software domain
> (`ProjectState`/`Spec`/`Plan`); they move here after a generification pass.
