// Pure state-machine core for the studio pipeline. `decide()` maps the current
// status + an incoming event to the next action, with idempotency built in:
// an event that doesn't match the current status is a no-op (absorbs duplicate
// / out-of-order trigger delivery). See P0-DETAIL.md §2 (transition table).
import type { PipelineEvent, Status } from '../types.js'

export type Action =
  | { kind: 'invoke'; function_id: string; status: Status; bumpIteration?: boolean }
  | { kind: 'done'; status: 'delivered' }
  | { kind: 'fail'; status: 'failed'; reason?: string }
  | { kind: 'noop' }

export interface MachineState {
  status: Status
  iteration: number
  max_iterations: number
}

const FN = {
  spec: 'studio::intake::spec',
  plan: 'studio::design::plan',
  build: 'studio::build::run',
  qa: 'studio::qa::evaluate',
  deliver: 'studio::deliver::package',
} as const

export function decide(s: MachineState, e: PipelineEvent): Action {
  if (e.type === 'error') return { kind: 'fail', status: 'failed', reason: e.reason }

  switch (e.type) {
    case 'project.created':
      return s.status === 'intake'
        ? { kind: 'invoke', function_id: FN.spec, status: 'intake' }
        : noop()

    case 'spec.ready':
      return s.status === 'intake'
        ? { kind: 'invoke', function_id: FN.plan, status: 'design' }
        : noop()

    case 'plan.ready':
      return s.status === 'design'
        ? { kind: 'invoke', function_id: FN.build, status: 'building', bumpIteration: true }
        : noop()

    case 'build.done':
      return s.status === 'building' || s.status === 'revising'
        ? { kind: 'invoke', function_id: FN.qa, status: 'qa' }
        : noop()

    case 'qa.passed':
      return s.status === 'qa'
        ? { kind: 'invoke', function_id: FN.deliver, status: 'delivering' }
        : noop()

    case 'qa.failed':
      if (s.status !== 'qa') return noop()
      return s.iteration < s.max_iterations
        ? { kind: 'invoke', function_id: FN.build, status: 'revising', bumpIteration: true }
        : { kind: 'fail', status: 'failed', reason: 'max_iterations reached' }

    case 'delivered':
      return s.status === 'delivering' ? { kind: 'done', status: 'delivered' } : noop()

    default:
      return noop()
  }
}

/** Terminal states never transition further. */
export function isTerminal(status: Status): boolean {
  return status === 'delivered' || status === 'failed'
}

function noop(): Action {
  return { kind: 'noop' }
}
