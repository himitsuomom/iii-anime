// Account/provider fallback logic (ported from 9router accountFallback.js).
import { BACKOFF_CONFIG, ERROR_RULES, TRANSIENT_COOLDOWN_MS } from './errorConfig'

export interface FallbackDecision {
  shouldFallback: boolean
  cooldownMs: number
  newBackoffLevel?: number
}

/**
 * Exponential backoff cooldown for rate limits.
 * Level 1: 2s, Level 2: 4s, Level 3: 8s... capped at max.
 */
export function getQuotaCooldown(backoffLevel = 0): number {
  const level = Math.max(0, backoffLevel - 1)
  const cooldown = BACKOFF_CONFIG.base * 2 ** level
  return Math.min(cooldown, BACKOFF_CONFIG.max)
}

/**
 * Classify an upstream error and decide cooldown. Config-driven: matches
 * ERROR_RULES top-to-bottom (text rules first, then status).
 */
export function checkFallbackError(
  status: number,
  errorText: unknown,
  backoffLevel = 0,
): FallbackDecision {
  const lowerError = errorText
    ? (typeof errorText === 'string' ? errorText : JSON.stringify(errorText)).toLowerCase()
    : ''

  for (const rule of ERROR_RULES) {
    if (rule.text && lowerError && lowerError.includes(rule.text)) {
      if (rule.backoff) {
        const newLevel = Math.min(backoffLevel + 1, BACKOFF_CONFIG.maxLevel)
        return {
          shouldFallback: true,
          cooldownMs: getQuotaCooldown(newLevel),
          newBackoffLevel: newLevel,
        }
      }
      return { shouldFallback: true, cooldownMs: rule.cooldownMs ?? TRANSIENT_COOLDOWN_MS }
    }

    if (rule.status && rule.status === status) {
      if (rule.backoff) {
        const newLevel = Math.min(backoffLevel + 1, BACKOFF_CONFIG.maxLevel)
        return {
          shouldFallback: true,
          cooldownMs: getQuotaCooldown(newLevel),
          newBackoffLevel: newLevel,
        }
      }
      return { shouldFallback: true, cooldownMs: rule.cooldownMs ?? TRANSIENT_COOLDOWN_MS }
    }
  }

  return { shouldFallback: true, cooldownMs: TRANSIENT_COOLDOWN_MS }
}

/** In-memory runtime state tracked per provider. */
export interface ProviderState {
  rateLimitedUntil: number | null
  backoffLevel: number
  lastError: { status: number; message: string; timestamp: string } | null
  status: 'active' | 'error'
}

export function newProviderState(): ProviderState {
  return { rateLimitedUntil: null, backoffLevel: 0, lastError: null, status: 'active' }
}

/** True when the provider is still inside its cooldown window. */
export function isProviderUnavailable(state: ProviderState, now = Date.now()): boolean {
  if (!state.rateLimitedUntil) return false
  return state.rateLimitedUntil > now
}

/** Reset provider state after a successful request. */
export function resetProviderState(state: ProviderState): void {
  state.rateLimitedUntil = null
  state.backoffLevel = 0
  state.lastError = null
  state.status = 'active'
}

/** Apply error state + cooldown to a provider after a failed request. */
export function applyErrorState(
  state: ProviderState,
  status: number,
  errorText: string,
): FallbackDecision {
  const decision = checkFallbackError(status, errorText, state.backoffLevel)
  state.rateLimitedUntil = decision.cooldownMs > 0 ? Date.now() + decision.cooldownMs : null
  state.backoffLevel = decision.newBackoffLevel ?? state.backoffLevel
  state.lastError = { status, message: errorText, timestamp: new Date().toISOString() }
  state.status = 'error'
  return decision
}

/** Human-readable "reset after Xm Ys" for a cooldown timestamp. */
export function formatRetryAfter(rateLimitedUntil: number | null): string {
  if (!rateLimitedUntil) return ''
  const diffMs = rateLimitedUntil - Date.now()
  if (diffMs <= 0) return 'reset after 0s'
  const totalSec = Math.ceil(diffMs / 1000)
  const h = Math.floor(totalSec / 3600)
  const m = Math.floor((totalSec % 3600) / 60)
  const s = totalSec % 60
  const parts: string[] = []
  if (h > 0) parts.push(`${h}h`)
  if (m > 0) parts.push(`${m}m`)
  if (s > 0 || parts.length === 0) parts.push(`${s}s`)
  return `reset after ${parts.join(' ')}`
}
