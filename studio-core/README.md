# @iii/studio-core

Shared core for iii AI factories. Hosts the cross-factory code so multiple
factories (e.g. [`app-studio`](../app-studio), [`video-studio`](../video-studio))
run on one engine and reuse the same mechanism.

- `src/assets.ts` — integrate your existing Claude assets (skills/MCP/plugins/
  subagents/settings/model) into factory agents. `assetArgs()` builds the CLI
  flags; `assetsFromEnv()` reads a default bundle from env.
- `src/factory.ts` — `FactoryDescriptor` + registry: per-factory namespacing
  (route prefix / state scope / queue) with collision checks.

See **[MULTI-FACTORY.md](./MULTI-FACTORY.md)** for the integration guide,
production deployment, and the readiness checklist, and
[`deploy/multi-factory.local.yml`](./deploy/multi-factory.local.yml) for a
one-engine, multi-factory config.

```bash
cd studio-core && pnpm exec tsx --test "src/**/*.test.ts"   # 5 tests
```

> Roadmap: the execution sandbox, store, wiki, brain, and build backends are
> shared in practice and will physically move under this package next, so
> factories depend only on `@iii/studio-core`.
