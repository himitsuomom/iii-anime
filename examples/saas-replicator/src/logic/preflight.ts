/**
 * Pure preflight checks (no iii-sdk / node imports — unit-testable).
 *
 * Validates that the environment can actually run before the orchestrator
 * starts: in live mode it requires `provider-anthropic` + `ANTHROPIC_API_KEY`;
 * it surfaces informational notes about optional workers (`provider-kimi`
 * enables debate; missing `iii-sandbox` means Phase 3 tests run in the local
 * child-process executor instead of a microVM).
 */

export interface PreflightFacts {
  mode: 'live' | 'stub'
  hasAnthropicKey: boolean
  /** Worker names visible on the bus (e.g. from `listWorkers`). */
  workers: string[]
}

export interface PreflightReport {
  ok: boolean
  /** Blocking issues that should stop a live run. */
  problems: string[]
  /** Non-blocking, informational findings. */
  notes: string[]
}

const hasWorker = (workers: string[], name: string): boolean =>
  workers.some((w) => typeof w === 'string' && w.includes(name))

export function buildPreflightReport(facts: PreflightFacts): PreflightReport {
  const problems: string[] = []
  const notes: string[] = []

  if (facts.mode === 'stub') {
    notes.push('stub mode: no API keys or provider workers required')
  } else {
    if (!hasWorker(facts.workers, 'provider-anthropic')) {
      problems.push('live mode requires a `provider-anthropic` worker (iii worker add provider-anthropic)')
    }
    if (!facts.hasAnthropicKey) {
      problems.push('live mode requires ANTHROPIC_API_KEY to be set')
    }
  }

  notes.push(
    hasWorker(facts.workers, 'provider-kimi')
      ? 'provider-kimi present: analyzer/visualizer/tester/swarm auto-rebind to KIMI; debate enabled'
      : 'provider-kimi absent: running Claude-only (debate degrades to self-critique)',
  )
  notes.push(
    hasWorker(facts.workers, 'iii-sandbox')
      ? 'iii-sandbox present: Phase 3 tests run in an isolated microVM'
      : 'iii-sandbox absent: Phase 3 tests run in the local child-process executor (dev fallback)',
  )
  if (!hasWorker(facts.workers, 'approval-gate')) {
    notes.push('approval-gate absent: Phase 4 auto-approves before deploy')
  }

  return { ok: problems.length === 0, problems, notes }
}
