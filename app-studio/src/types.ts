// Shared domain types for the app-studio pipeline. See app-studio/P0-DETAIL.md
// and app-studio/SANDBOX-AND-BUILD-LOOP.md for the design these encode.

export type Status =
  | 'intake'
  | 'design'
  | 'building'
  | 'qa'
  | 'revising'
  | 'awaiting_approval'
  | 'delivering'
  | 'delivered'
  | 'failed'

export interface Spec {
  goal: string
  features: string[]
  acceptance: string[]
  constraints?: string[]
  assumptions: string[]
}

export interface Plan {
  /** App-type id; validated against the adapter registry. */
  app_type: string
  stack: string[]
  tasks: string[]
  build_cmd: string
  test_cmd: string
  run_cmd?: string
}

export interface RubricCheck {
  id: string
  cmd: string
  expect: 'exit0'
}

export interface Rubric {
  hard: RubricCheck[]
  soft?: Array<{ id: string; check: string }>
}

export interface QaResult {
  passed: boolean
  failures: string[]
  score: number
  logs_ref?: string
}

export interface Artifacts {
  files: string[]
  repo_url?: string
  preview_url?: string
  /** Command to start the app locally (from the plan's run_cmd), if any. */
  preview_cmd?: string
}

export interface ProjectState {
  project_id: string
  idea: string
  status: Status
  iteration: number
  max_iterations: number
  /** When true, the pipeline pauses at awaiting_approval after QA passes. */
  require_approval?: boolean
  workdir: string
  spec?: Spec
  plan?: Plan
  last_qa?: QaResult
  artifacts?: Artifacts
  /** Accumulated build spend (from the Claude backend's reported usage). */
  usage?: { cost_usd: number; turns: number; build_attempts: number }
  trace_id?: string
  updated_at: string
}

export type PipelineEvent =
  | { type: 'project.created' }
  | { type: 'spec.ready' }
  | { type: 'plan.ready' }
  | { type: 'build.done' }
  | { type: 'qa.passed' }
  | { type: 'qa.failed' }
  | { type: 'approved' }
  | { type: 'rejected'; reason?: string }
  | { type: 'delivered' }
  | { type: 'error'; reason?: string }

export const DEFAULT_MAX_ITERATIONS = 5
