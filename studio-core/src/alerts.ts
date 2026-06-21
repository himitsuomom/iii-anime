// Lightweight operational alerts derived from project state (the data is already
// there; this turns it into actionable signals). Domain-agnostic: works on any
// item with a status + updated_at. Surface via an HTTP route and/or scrape.

export interface AlertItem {
  project_id: string
  status: string
  updated_at: string
  last_qa?: { passed: boolean }
}

export interface AlertOptions {
  now?: number
  /** A non-terminal project idle longer than this is "stuck". */
  stuckMs?: number
  /** Terminal failures ≥ this fraction of finished projects → failure-spike alert. */
  failureRateThreshold?: number
}

export interface Alerts {
  stuck: string[]
  failed: number
  delivered: number
  failure_rate: number
  failure_spike: boolean
  alerts: string[]
}

const TERMINAL = new Set(['delivered', 'failed'])

export function detectAlerts(items: AlertItem[], opts: AlertOptions = {}): Alerts {
  const now = opts.now ?? Date.now()
  const stuckMs = opts.stuckMs ?? 10 * 60_000
  const threshold = opts.failureRateThreshold ?? 0.5

  const stuck: string[] = []
  let failed = 0
  let delivered = 0
  for (const it of items) {
    if (it.status === 'failed') failed++
    else if (it.status === 'delivered') delivered++
    else if (!TERMINAL.has(it.status)) {
      const age = now - Date.parse(it.updated_at)
      if (Number.isFinite(age) && age >= stuckMs) stuck.push(it.project_id)
    }
  }
  const finished = failed + delivered
  const failure_rate = finished > 0 ? failed / finished : 0
  const failure_spike = finished >= 3 && failure_rate >= threshold

  const messages: string[] = []
  if (stuck.length) messages.push(`${stuck.length} project(s) stuck > ${Math.round(stuckMs / 60000)}m: ${stuck.join(', ')}`)
  if (failure_spike) messages.push(`failure spike: ${(failure_rate * 100).toFixed(0)}% of ${finished} finished projects failed`)

  return { stuck, failed, delivered, failure_rate, failure_spike, alerts: messages }
}
