import type { ApiRequest, ApiResponse } from 'iii-sdk'
import { compressMessages, formatRtkLog } from './rtk'
import { iii } from './iii'
import { loadProviders, type ProviderConfig } from './routing/providers'
import { type LoggerLike, Router } from './routing/router'

// Minimal structured logger. The iii SDK does not export a public Logger, so we
// keep a tiny console-backed one matching the LoggerLike shape the Router expects.
const makeLogger = (scope: string): LoggerLike => ({
  info: (msg, meta) => console.log(`[${scope}] ${msg}`, meta ?? ''),
  warn: (msg, meta) => console.warn(`[${scope}] ${msg}`, meta ?? ''),
  error: (msg, meta) => console.error(`[${scope}] ${msg}`, meta ?? ''),
})

// Default provider tiers. Override at runtime with III_ROUTER_PROVIDERS (JSON array).
// Tiers are tried in order: subscription → cheap → free.
const DEFAULT_PROVIDERS: ProviderConfig[] = [
  {
    id: 'openai',
    tier: 'subscription',
    format: 'openai',
    baseUrl: process.env.OPENAI_BASE_URL ?? 'https://api.openai.com/v1',
    // biome-ignore lint/suspicious/noTemplateCurlyInString: ${ENV} is our own placeholder syntax, resolved at request time
    apiKey: '${OPENAI_API_KEY}',
  },
  {
    id: 'anthropic',
    tier: 'cheap',
    format: 'anthropic',
    baseUrl: process.env.ANTHROPIC_BASE_URL ?? 'https://api.anthropic.com/v1',
    // biome-ignore lint/suspicious/noTemplateCurlyInString: ${ENV} is our own placeholder syntax, resolved at request time
    apiKey: '${ANTHROPIC_API_KEY}',
  },
]

const router = new Router(loadProviders(DEFAULT_PROVIDERS), {
  rtk: process.env.III_ROUTER_RTK !== 'false',
})

const logger = makeLogger('iii-router')

// ── HTTP helper (mirrors iii-example useApi) ──────────────────────────────────
const useApi = (
  config: {
    api_path: string
    http_method: string
    description?: string
    metadata?: Record<string, unknown>
  },
  // biome-ignore lint/suspicious/noExplicitAny: handler body is dynamically shaped
  handler: (req: ApiRequest<any>, log: LoggerLike) => Promise<ApiResponse>,
) => {
  const function_id = `api::${config.http_method.toLowerCase()}::${config.api_path}`
  const fnLogger = makeLogger(function_id)
  // biome-ignore lint/suspicious/noExplicitAny: handler body is dynamically shaped
  iii.registerFunction(function_id, (req: ApiRequest<any>) => handler(req, fnLogger), {
    metadata: config.metadata,
  })
  iii.registerTrigger({
    type: 'http',
    function_id,
    config: {
      api_path: config.api_path,
      http_method: config.http_method,
      description: config.description,
      metadata: config.metadata,
    },
  })
}

// ── Directly-callable functions (usable via iii.trigger from other workers) ──

// router::route — RTK-compress + tiered fallback routing. Returns the upstream body.
iii.registerFunction(
  'router::route',
  // biome-ignore lint/suspicious/noExplicitAny: invocation payload is dynamically shaped
  async (input: { body: Record<string, any>; rtk?: boolean; timeoutMs?: number }) => {
    return router.route({ body: input.body, rtk: input.rtk, timeoutMs: input.timeoutMs }, logger)
  },
  { metadata: { tags: ['router'] } },
)

// rtk::compress — standalone token saver. Compresses tool_result content in a body.
iii.registerFunction(
  'rtk::compress',
  // biome-ignore lint/suspicious/noExplicitAny: invocation payload is dynamically shaped
  async (input: { body: Record<string, any>; enabled?: boolean }) => {
    const body = structuredClone(input.body)
    const stats = compressMessages(body, input.enabled ?? true)
    return { body, stats, log: formatRtkLog(stats) }
  },
  { metadata: { tags: ['rtk'] } },
)

// router::status — provider availability snapshot.
iii.registerFunction('router::status', async () => router.status(), {
  metadata: { tags: ['router'] },
})

// ── HTTP endpoints (OpenAI- and Anthropic-compatible) ────────────────────────

const handleChat = async (
  req: ApiRequest<Record<string, unknown>>,
  log: LoggerLike,
): Promise<ApiResponse> => {
  const body = req.body
  if (!body || typeof body !== 'object') {
    return { status_code: 400, body: { error: { message: 'Request body must be a JSON object' } } }
  }
  const result = await router.route({ body }, log)
  return {
    status_code: result.status,
    headers: {
      'content-type': 'application/json',
      'x-iii-router-provider': result.provider ?? 'none',
      'x-iii-router-rtk-saved': String(
        result.rtk ? result.rtk.bytesBefore - result.rtk.bytesAfter : 0,
      ),
    },
    body: result.body,
  }
}

useApi(
  {
    api_path: 'v1/chat/completions',
    http_method: 'POST',
    description: 'OpenAI-compatible chat completions with RTK token saving + tiered auto-fallback',
    metadata: { tags: ['router', 'openai'] },
  },
  handleChat,
)

useApi(
  {
    api_path: 'v1/messages',
    http_method: 'POST',
    description: 'Anthropic-compatible messages with RTK token saving + tiered auto-fallback',
    metadata: { tags: ['router', 'anthropic'] },
  },
  handleChat,
)

useApi(
  {
    api_path: 'router/status',
    http_method: 'GET',
    description: 'Provider availability + cooldown snapshot',
    metadata: { tags: ['router'] },
  },
  async () => ({ status_code: 200, body: { providers: router.status() } }),
)

logger.info('iii-router worker registered', {
  providers: router.status().map(p => `${p.id}:${p.tier}`),
})
