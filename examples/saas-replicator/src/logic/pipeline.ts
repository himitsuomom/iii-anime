/**
 * Pure 4-phase pipeline logic (no iii-sdk imports — unit-testable).
 *
 * Phase 1 UI analysis (swarm fan-out) -> Phase 2 PRD -> Phase 3 implement+test
 * -> Phase 4 visualize+deploy. The orchestrator persists `ProjectState` in
 * iii-state; these helpers decide what happens next from that state alone.
 */

export type Phase = 1 | 2 | 3 | 4
export type Status = Phase | 'done'

export interface ScreenInput {
  id: string
  /** Image URL / data-uri / reference passed to the analyzer role. */
  source?: string
}

export interface ProjectState {
  projectId: string
  target: string
  requirements: string
  status: Status
  phase1: {
    /** Total screens enqueued for analysis. */
    total: number
    /** Per-screen analysis result, keyed by screen id. */
    screens: Record<string, unknown>
  }
  artifacts: {
    phase1Review?: unknown
    prd?: unknown
    /** Architecture decision from the Phase 3 debate/self-critique step. */
    architecture?: unknown
    implementation?: unknown
    /** Generated codebase (real file contents) materialized + tested in Phase 3. */
    codebase?: unknown
    tests?: unknown
    visuals?: unknown
    deployment?: unknown
    /** Supervisor review rounds recorded per supervised artifact. */
    reviews?: Record<string, unknown>
  }
}

export interface StartInput {
  target: string
  requirements: string
  screenshots: ScreenInput[]
}

export function initialState(projectId: string, input: StartInput): ProjectState {
  return {
    projectId,
    target: input.target,
    requirements: input.requirements,
    status: input.screenshots.length > 0 ? 1 : 2,
    phase1: { total: input.screenshots.length, screens: {} },
    artifacts: {},
  }
}

/** Phase 1 is complete once every enqueued screen has reported a result. */
export function isPhase1Complete(state: Pick<ProjectState, 'phase1'>): boolean {
  return phase1Complete(state.phase1.total, Object.keys(state.phase1.screens).length)
}

/** Numeric form of the Phase 1 completion rule (single source of truth). */
export function phase1Complete(total: number, analyzed: number): boolean {
  return total === 0 || analyzed >= total
}

/** The phase that should run after the given one (`done` after Phase 4). */
export function nextStatus(status: Status): Status {
  if (status === 'done') return 'done'
  if (status === 4) return 'done'
  return (status + 1) as Phase
}

/** Fraction 0..1 of analyzed screens (1 when there is nothing to analyze). */
export function phase1Progress(state: Pick<ProjectState, 'phase1'>): number {
  const { total, screens } = state.phase1
  if (total === 0) return 1
  return Math.min(1, Object.keys(screens).length / total)
}
