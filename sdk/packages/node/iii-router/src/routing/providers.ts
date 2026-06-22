// Provider tier configuration + endpoint / auth resolution.

export type ProviderFormat = 'openai' | 'anthropic'
export type ProviderTier = 'subscription' | 'cheap' | 'free'

export interface ProviderConfig {
  /** Unique id, e.g. "claude-code", "glm", "kiro". */
  id: string
  /** Routing tier — providers are tried subscription → cheap → free. */
  tier: ProviderTier
  /** Wire format expected by the upstream. */
  format: ProviderFormat
  /** Base URL, e.g. "https://api.openai.com/v1". */
  baseUrl: string
  /** Bearer/x-api-key credential. Supports ${ENV_VAR} interpolation. */
  apiKey?: string
  /** Optional model override sent to the upstream. */
  model?: string
  /** Extra headers merged onto the upstream request. */
  headers?: Record<string, string>
}

const TIER_ORDER: Record<ProviderTier, number> = {
  subscription: 0,
  cheap: 1,
  free: 2,
}

/** Resolve ${ENV_VAR} placeholders against process.env. */
function interpolate(value: string | undefined): string | undefined {
  if (!value) return value
  return value.replace(/\$\{(\w+)\}/g, (_, name) => process.env[name] ?? '')
}

/** Sort providers by tier priority (stable within a tier). */
export function sortByTier(providers: ProviderConfig[]): ProviderConfig[] {
  return [...providers].sort((a, b) => TIER_ORDER[a.tier] - TIER_ORDER[b.tier])
}

/** Build the upstream URL for a provider + detected request format. */
export function buildUpstreamUrl(provider: ProviderConfig): string {
  const base = provider.baseUrl.replace(/\/$/, '')
  if (provider.format === 'anthropic') return `${base}/messages`
  return `${base}/chat/completions`
}

/** Build the auth + content headers for a provider request. */
export function buildHeaders(provider: ProviderConfig): Record<string, string> {
  const headers: Record<string, string> = {
    'content-type': 'application/json',
    ...(provider.headers ?? {}),
  }
  const apiKey = interpolate(provider.apiKey)
  if (apiKey) {
    if (provider.format === 'anthropic') {
      headers['x-api-key'] = apiKey
      headers['anthropic-version'] = headers['anthropic-version'] ?? '2023-06-01'
    } else {
      headers.authorization = `Bearer ${apiKey}`
    }
  }
  return headers
}

/**
 * Load provider config from the III_ROUTER_PROVIDERS env var (JSON array) or
 * fall back to a single config passed in. Returns providers sorted by tier.
 */
export function loadProviders(fallback: ProviderConfig[] = []): ProviderConfig[] {
  const raw = process.env.III_ROUTER_PROVIDERS
  if (raw) {
    try {
      const parsed = JSON.parse(raw) as ProviderConfig[]
      if (Array.isArray(parsed) && parsed.length > 0) return sortByTier(parsed)
    } catch (e) {
      const message = e instanceof Error ? e.message : String(e)
      console.warn('[router] failed to parse III_ROUTER_PROVIDERS:', message)
    }
  }
  return sortByTier(fallback)
}

/** Detect request wire format from body structure (subset of 9router detectFormat). */
// biome-ignore lint/suspicious/noExplicitAny: request bodies are dynamically shaped
export function detectFormat(body: Record<string, any>): ProviderFormat {
  // Anthropic Messages API carries a top-level `system` string/array plus `messages`,
  // and uses `max_tokens` (required). OpenAI-specific fields below take precedence.
  if (
    body.stream_options ||
    body.response_format ||
    body.logprobs !== undefined ||
    body.top_logprobs !== undefined ||
    body.frequency_penalty !== undefined ||
    body.presence_penalty !== undefined ||
    body.logit_bias
  ) {
    return 'openai'
  }
  if (body.anthropic_version || (body.system !== undefined && Array.isArray(body.messages))) {
    return 'anthropic'
  }
  return 'openai'
}
