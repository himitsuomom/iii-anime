// Crash recovery. Webhook/trigger delivery isn't guaranteed, and the container
// is ephemeral, so a project can be left mid-pipeline. resume() re-enters the
// current stage and drives it forward; sweep() does that for every stuck,
// non-terminal project. See IDEMPOTENCY-RESUME.md §4–5.
import type { FunctionId, StudioDeps } from '../pipeline/handlers.js'
import { handlerFor } from '../pipeline/handlers.js'
import type { Status } from '../types.js'
import { advance } from './apply.js'
import { isTerminal } from './machine.js'

/** The handler that owns each non-terminal status (re-entered on resume). */
const STAGE_FN: Partial<Record<Status, FunctionId>> = {
  intake: 'studio::intake::spec',
  design: 'studio::design::plan',
  building: 'studio::build::run',
  revising: 'studio::build::run',
  qa: 'studio::qa::evaluate',
  delivering: 'studio::deliver::package',
}

/** Re-run the current stage for one project, then advance to a terminal state. */
export async function resume(deps: StudioDeps, projectId: string): Promise<boolean> {
  const s = await deps.store.get(projectId)
  if (!s || isTerminal(s.status)) return false
  const fn = STAGE_FN[s.status]
  if (!fn) return false
  const event = await handlerFor(deps, fn)(projectId)
  await advance(deps, projectId, event)
  return true
}

export interface SweepOptions {
  /** Only resume projects whose updated_at is older than this many ms. */
  stuckMs?: number
  now?: () => number
}

/** Resume every non-terminal project that looks stuck. Returns ids resumed. */
export async function sweep(deps: StudioDeps, opts: SweepOptions = {}): Promise<string[]> {
  const stuckMs = opts.stuckMs ?? 5 * 60_000
  const now = opts.now ? opts.now() : Date.now()
  const all = await deps.store.list()
  const resumed: string[] = []
  for (const s of all) {
    if (isTerminal(s.status)) continue
    const age = now - Date.parse(s.updated_at)
    if (Number.isFinite(age) && age < stuckMs) continue
    if (await resume(deps, s.project_id)) resumed.push(s.project_id)
  }
  return resumed
}
