import Anthropic from '@anthropic-ai/sdk'

/**
 * Default model for all generation. Per the claude-api guidance we default to
 * the most capable Opus-tier model; callers can override per request if needed.
 */
export const MODEL = 'claude-opus-4-8'

let cached: Anthropic | null = null

/**
 * Returns a shared Anthropic client, or `null` when no API key is configured.
 * Routes translate `null` into a 503 so the UI can show a clear message instead
 * of the whole app falling over.
 */
export function getClient(): Anthropic | null {
  const apiKey = process.env.ANTHROPIC_API_KEY
  if (!apiKey) return null
  if (!cached) cached = new Anthropic({ apiKey })
  return cached
}

export function hasApiKey(): boolean {
  return Boolean(process.env.ANTHROPIC_API_KEY)
}
