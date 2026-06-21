// Orchestrator apply layer — turns a pipeline event into state transitions and
// the next handler invocation, using the pure decide() core. P0 runs handlers
// inline (the orchestrator drives the whole pipeline in one async call); the
// build<->qa loop and max_iterations cap come from decide().
import { handlerFor, type FunctionId, type StudioDeps } from '../pipeline/handlers.js'
import type { PipelineEvent } from '../types.js'
import { decide, type MachineState } from './machine.js'

export interface AdvanceOptions {
  /** Safety net against an unexpected non-terminating loop. */
  maxSteps?: number
}

/**
 * Drive the pipeline forward from an event until it reaches a terminal state
 * (delivered/failed) or a no-op. Returns the number of handler invocations.
 */
export async function advance(
  deps: StudioDeps,
  projectId: string,
  event: PipelineEvent,
  opts: AdvanceOptions = {},
): Promise<number> {
  const maxSteps = opts.maxSteps ?? 100
  let current = event
  let steps = 0

  for (let i = 0; i < maxSteps; i++) {
    const s = await deps.store.get(projectId)
    if (!s) throw new Error(`unknown project: ${projectId}`)
    const ms: MachineState = {
      status: s.status,
      iteration: s.iteration,
      max_iterations: s.max_iterations,
    }
    const action = decide(ms, current)

    if (action.kind === 'noop') return steps
    if (action.kind === 'done') {
      await deps.store.update(projectId, { status: 'delivered' })
      return steps
    }
    if (action.kind === 'fail') {
      await deps.store.update(projectId, { status: 'failed' })
      return steps
    }

    // action.kind === 'invoke'
    await deps.store.update(projectId, {
      status: action.status,
      iteration: s.iteration + (action.bumpIteration ? 1 : 0),
    })
    const handler = handlerFor(deps, action.function_id as FunctionId)
    current = await handler(projectId)
    steps++
  }

  throw new Error(`advance exceeded ${maxSteps} steps for ${projectId} (possible loop)`)
}
