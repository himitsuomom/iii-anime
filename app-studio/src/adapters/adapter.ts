// App-type adapter: the per-type plug point that makes the studio support many
// kinds of app without the build/qa code knowing the specifics. Adding a type
// is one file + one register() call. See app-studio/DESIGN.md §3.
import type { Plan, Rubric } from '../types.js'

export interface AppTypeAdapter {
  /** Stable id used as Plan.app_type. */
  id: string
  /** One-line human description. */
  title: string
  /** Guidance injected into the design prompt so the plan fits this type. */
  designGuidance: string
  /** Build the QA rubric (the "is it done" checks) for a plan of this type. */
  rubric(plan: Plan): Rubric
  /** Extra executables this type needs available in the sandbox (P1). */
  extraAllowlist?: string[]
}
