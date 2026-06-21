import assert from 'node:assert/strict'
import { describe, test } from 'node:test'
import type { PipelineEvent } from '../types.js'
import { decide, isTerminal, type MachineState } from './machine.js'

const st = (over: Partial<MachineState> = {}): MachineState => ({
  status: 'intake',
  iteration: 0,
  max_iterations: 5,
  ...over,
})

describe('decide — happy path', () => {
  const cases: Array<[MachineState['status'], PipelineEvent, string]> = [
    ['intake', { type: 'project.created' }, 'studio::intake::spec'],
    ['intake', { type: 'spec.ready' }, 'studio::design::plan'],
    ['design', { type: 'plan.ready' }, 'studio::build::run'],
    ['building', { type: 'build.done' }, 'studio::qa::evaluate'],
    ['qa', { type: 'qa.passed' }, 'studio::deliver::package'],
  ]
  for (const [status, event, fn] of cases) {
    test(`${status} + ${event.type} -> ${fn}`, () => {
      const a = decide(st({ status }), event)
      assert.equal(a.kind, 'invoke')
      if (a.kind === 'invoke') assert.equal(a.function_id, fn)
    })
  }

  test('delivering + delivered -> done', () => {
    const a = decide(st({ status: 'delivering' }), { type: 'delivered' })
    assert.equal(a.kind, 'done')
  })
})

describe('decide — build iteration loop', () => {
  test('plan.ready bumps iteration into building', () => {
    const a = decide(st({ status: 'design' }), { type: 'plan.ready' })
    assert.equal(a.kind, 'invoke')
    if (a.kind === 'invoke') assert.equal(a.bumpIteration, true)
  })

  test('qa.failed under the cap revises (and bumps iteration)', () => {
    const a = decide(st({ status: 'qa', iteration: 2, max_iterations: 5 }), { type: 'qa.failed' })
    assert.equal(a.kind, 'invoke')
    if (a.kind === 'invoke') {
      assert.equal(a.status, 'revising')
      assert.equal(a.function_id, 'studio::build::run')
      assert.equal(a.bumpIteration, true)
    }
  })

  test('qa.failed at the cap fails the project', () => {
    const a = decide(st({ status: 'qa', iteration: 5, max_iterations: 5 }), { type: 'qa.failed' })
    assert.equal(a.kind, 'fail')
  })

  test('revising + build.done returns to qa', () => {
    const a = decide(st({ status: 'revising' }), { type: 'build.done' })
    assert.equal(a.kind, 'invoke')
    if (a.kind === 'invoke') assert.equal(a.function_id, 'studio::qa::evaluate')
  })
})

describe('decide — approval gate', () => {
  test('qa.passed with requireApproval waits for sign-off', () => {
    const a = decide(st({ status: 'qa', requireApproval: true }), { type: 'qa.passed' })
    assert.equal(a.kind, 'wait')
    if (a.kind === 'wait') assert.equal(a.status, 'awaiting_approval')
  })
  test('qa.passed without requireApproval delivers directly', () => {
    const a = decide(st({ status: 'qa' }), { type: 'qa.passed' })
    assert.equal(a.kind, 'invoke')
    if (a.kind === 'invoke') assert.equal(a.function_id, 'studio::deliver::package')
  })
  test('approved while awaiting -> deliver', () => {
    const a = decide(st({ status: 'awaiting_approval' }), { type: 'approved' })
    assert.equal(a.kind, 'invoke')
    if (a.kind === 'invoke') assert.equal(a.status, 'delivering')
  })
  test('rejected while awaiting -> fail', () => {
    const a = decide(st({ status: 'awaiting_approval' }), { type: 'rejected', reason: 'nope' })
    assert.equal(a.kind, 'fail')
    if (a.kind === 'fail') assert.equal(a.reason, 'nope')
  })
  test('approved when not awaiting is a no-op', () => {
    assert.equal(decide(st({ status: 'qa' }), { type: 'approved' }).kind, 'noop')
  })
})

describe('decide — idempotency / out-of-order', () => {
  test('duplicate spec.ready after moving on is a no-op', () => {
    assert.equal(decide(st({ status: 'design' }), { type: 'spec.ready' }).kind, 'noop')
  })
  test('plan.ready while still in intake is a no-op', () => {
    assert.equal(decide(st({ status: 'intake' }), { type: 'plan.ready' }).kind, 'noop')
  })
  test('qa.passed while building is a no-op', () => {
    assert.equal(decide(st({ status: 'building' }), { type: 'qa.passed' }).kind, 'noop')
  })
})

describe('decide — failures', () => {
  test('error event always fails', () => {
    const a = decide(st({ status: 'building' }), { type: 'error', reason: 'boom' })
    assert.equal(a.kind, 'fail')
    if (a.kind === 'fail') assert.equal(a.reason, 'boom')
  })
  test('isTerminal', () => {
    assert.equal(isTerminal('delivered'), true)
    assert.equal(isTerminal('failed'), true)
    assert.equal(isTerminal('building'), false)
  })
})
