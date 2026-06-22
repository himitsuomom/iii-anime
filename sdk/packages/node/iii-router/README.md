# iii-router

An iii worker that brings two [9router](https://github.com/decolua/9router) features into the
iii Worker/Function/Trigger model:

- **RTK token saver** — compresses `tool_result` content in LLM request bodies (git diff/status,
  grep, find, ls, tree, build output, line-numbered file dumps…), typically saving 20–40% tokens.
- **Tiered AI routing + auto-fallback** — forwards a request through a list of providers ordered
  `subscription → cheap → free`, applying config-driven error classification with exponential
  backoff and per-provider cooldowns so a request never stalls on one exhausted provider.

## Primitives

| Kind | Id | Purpose |
| --- | --- | --- |
| Function | `router::route` | RTK-compress + tiered fallback routing; returns the upstream body. |
| Function | `rtk::compress` | Standalone token saver; returns the compressed body + stats. |
| Function | `router::status` | Provider availability + cooldown snapshot. |
| Trigger (HTTP) | `POST /v1/chat/completions` | OpenAI-compatible endpoint. |
| Trigger (HTTP) | `POST /v1/messages` | Anthropic-compatible endpoint. |
| Trigger (HTTP) | `GET /router/status` | Provider status snapshot. |

Other workers can route through it directly:

```ts
const result = await iii.trigger({
  function_id: 'router::route',
  payload: { body: { model: 'gpt-4o', messages: [...] } },
})
```

## Configuration

Providers are tried in tier order. Configure them with the `III_ROUTER_PROVIDERS` env var
(a JSON array); otherwise the defaults in `src/index.ts` (OpenAI → Anthropic) are used.

```jsonc
// III_ROUTER_PROVIDERS
[
  { "id": "claude-code", "tier": "subscription", "format": "anthropic",
    "baseUrl": "https://api.anthropic.com/v1", "apiKey": "${ANTHROPIC_API_KEY}" },
  { "id": "glm", "tier": "cheap", "format": "openai",
    "baseUrl": "https://api.z.ai/v1", "apiKey": "${GLM_API_KEY}", "model": "glm-4.6" },
  { "id": "opencode-free", "tier": "free", "format": "openai",
    "baseUrl": "https://opencode.ai/v1" }
]
```

`${ENV_VAR}` placeholders in `apiKey` are resolved at request time. Auth headers are set per
format (`authorization: Bearer …` for OpenAI, `x-api-key` for Anthropic).

| Env var | Default | Meaning |
| --- | --- | --- |
| `III_URL` | `ws://localhost:49134` | Engine WebSocket URL. |
| `III_ROUTER_PROVIDERS` | _(built-in defaults)_ | JSON array of providers. |
| `III_ROUTER_RTK` | `true` | Set `false` to disable RTK globally. |

## Run

```bash
pnpm install
# start the engine with the bundled config (serves HTTP on :20128)
cargo run --release -- --config sdk/packages/node/iii-router/config.yaml
# in another shell
pnpm --filter @iii-hq/iii-router dev
```

## Test

```bash
pnpm --filter @iii-hq/iii-router test
```

RTK and fallback logic are covered by `src/rtk.test.ts` and run without the engine.
