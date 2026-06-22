// Tiered AI router with RTK token saving + auto-fallback.
import { compressMessages, formatRtkLog, type RtkStats } from '../rtk'
import {
  applyErrorState,
  formatRetryAfter,
  isProviderUnavailable,
  newProviderState,
  type ProviderState,
  resetProviderState,
} from './fallback'
import { buildHeaders, buildUpstreamUrl, type ProviderConfig, sortByTier } from './providers'

export interface RouteRequest {
  // biome-ignore lint/suspicious/noExplicitAny: request bodies are dynamically shaped
  body: Record<string, any>
  /** Override RTK on/off for this request. */
  rtk?: boolean
  /** Per-request upstream timeout. */
  timeoutMs?: number
}

export interface RouteResult {
  status: number
  // biome-ignore lint/suspicious/noExplicitAny: upstream responses are dynamically shaped
  body: any
  /** Provider id that served the response. */
  provider: string | null
  /** RTK compression stats, if applied. */
  rtk: RtkStats | null
  /** Per-provider attempts with outcome. */
  attempts: Array<{ provider: string; status: number; error?: string }>
}

export interface LoggerLike {
  info: (msg: string, meta?: Record<string, unknown>) => void
  warn: (msg: string, meta?: Record<string, unknown>) => void
  error: (msg: string, meta?: Record<string, unknown>) => void
}

const DEFAULT_TIMEOUT_MS = 120_000

/**
 * The Router owns the provider list, their runtime cooldown state, and the
 * request loop: RTK-compress → try providers in tier order → fall back on error.
 */
export class Router {
  private providers: ProviderConfig[]
  private states = new Map<string, ProviderState>()
  private rtkEnabled: boolean

  constructor(providers: ProviderConfig[], opts: { rtk?: boolean } = {}) {
    this.providers = sortByTier(providers)
    this.rtkEnabled = opts.rtk ?? true
    for (const p of this.providers) this.states.set(p.id, newProviderState())
  }

  /** Snapshot of provider availability for status endpoints. */
  status(): Array<{ id: string; tier: string; available: boolean; cooldown: string }> {
    const now = Date.now()
    return this.providers.map(p => {
      const state = this.states.get(p.id) ?? newProviderState()
      return {
        id: p.id,
        tier: p.tier,
        available: !isProviderUnavailable(state, now),
        cooldown: formatRetryAfter(state.rateLimitedUntil),
      }
    })
  }

  async route(req: RouteRequest, logger?: LoggerLike): Promise<RouteResult> {
    const rtkOn = req.rtk ?? this.rtkEnabled
    const stats = compressMessages(req.body, rtkOn)
    if (stats) {
      const line = formatRtkLog(stats)
      if (line) logger?.info(line)
    }

    const attempts: RouteResult['attempts'] = []
    const now = Date.now()
    let lastStatus = 503
    let lastError = 'no providers available'

    for (const provider of this.providers) {
      const state = this.states.get(provider.id) ?? newProviderState()
      if (isProviderUnavailable(state, now)) {
        attempts.push({
          provider: provider.id,
          status: 0,
          error: `cooldown (${formatRetryAfter(state.rateLimitedUntil)})`,
        })
        continue
      }

      try {
        const { status, body } = await this.dispatch(provider, req.body, req.timeoutMs)
        if (status >= 200 && status < 300) {
          resetProviderState(state)
          return { status, body, provider: provider.id, rtk: stats, attempts }
        }

        const errText = typeof body === 'string' ? body : JSON.stringify(body)
        const decision = applyErrorState(state, status, errText)
        attempts.push({ provider: provider.id, status, error: errText.slice(0, 200) })
        logger?.warn(
          `[router] ${provider.id} failed (${status}), cooldown ${decision.cooldownMs}ms — falling back`,
        )
        lastStatus = status
        lastError = errText
      } catch (e) {
        const message = e instanceof Error ? e.message : String(e)
        const decision = applyErrorState(state, 0, message)
        attempts.push({ provider: provider.id, status: 0, error: message.slice(0, 200) })
        logger?.warn(
          `[router] ${provider.id} threw (${message}), cooldown ${decision.cooldownMs}ms — falling back`,
        )
        lastStatus = 502
        lastError = message
      }
    }

    logger?.error('[router] all providers exhausted', { lastStatus, attempts })
    return {
      status: lastStatus,
      body: {
        error: { message: `All providers exhausted: ${lastError}`, type: 'router_exhausted' },
      },
      provider: null,
      rtk: stats,
      attempts,
    }
  }

  /** Forward a single request to one provider's upstream. */
  private async dispatch(
    provider: ProviderConfig,
    // biome-ignore lint/suspicious/noExplicitAny: request bodies are dynamically shaped
    body: Record<string, any>,
    timeoutMs = DEFAULT_TIMEOUT_MS,
    // biome-ignore lint/suspicious/noExplicitAny: upstream responses are dynamically shaped
  ): Promise<{ status: number; body: any }> {
    const url = buildUpstreamUrl(provider)
    const headers = buildHeaders(provider)
    const outBody = provider.model ? { ...body, model: provider.model } : body

    const controller = new AbortController()
    const timer = setTimeout(() => controller.abort(), timeoutMs)
    try {
      const res = await fetch(url, {
        method: 'POST',
        headers,
        body: JSON.stringify(outBody),
        signal: controller.signal,
      })
      const text = await res.text()
      let parsed: unknown = text
      try {
        parsed = JSON.parse(text)
      } catch {
        // leave as text
      }
      return { status: res.status, body: parsed }
    } finally {
      clearTimeout(timer)
    }
  }
}
