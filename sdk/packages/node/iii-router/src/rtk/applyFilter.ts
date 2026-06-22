import type { RtkFilter } from './constants'

// Port of apply_filter (catch_unwind equivalent).
// On panic/error: passthrough raw output + warn to stderr.
export function safeApply(fn: RtkFilter, text: string): string {
  if (typeof fn !== 'function') return text
  try {
    const out = fn(text)
    if (typeof out !== 'string') return text
    return out
  } catch (err) {
    const name = fn.filterName || fn.name || 'anonymous'
    const message = err instanceof Error ? err.message : String(err)
    console.warn(
      `[rtk] warning: filter '${name}' panicked — passing through raw output: ${message}`,
    )
    return text
  }
}
