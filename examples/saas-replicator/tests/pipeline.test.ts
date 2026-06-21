import assert from 'node:assert/strict'
import { test } from 'node:test'
import { initialState, isPhase1Complete, nextStatus, phase1Complete, phase1Progress } from '../src/logic/pipeline'

const start = (screens: number) => ({
  target: 'Trello',
  requirements: 'JP UI / PWA',
  screenshots: Array.from({ length: screens }, (_, i) => ({ id: `s${i}` })),
})

test('initialState starts at Phase 1 when screenshots exist, else Phase 2', () => {
  assert.equal(initialState('p1', start(3)).status, 1)
  assert.equal(initialState('p2', start(0)).status, 2)
  assert.equal(initialState('p1', start(3)).phase1.total, 3)
})

test('phase1Complete: numeric completion rule', () => {
  assert.equal(phase1Complete(3, 2), false)
  assert.equal(phase1Complete(3, 3), true)
  assert.equal(phase1Complete(0, 0), true) // nothing to analyze
})

test('isPhase1Complete agrees with the numeric rule', () => {
  assert.equal(isPhase1Complete({ phase1: { total: 2, screens: { a: 1 } } }), false)
  assert.equal(isPhase1Complete({ phase1: { total: 2, screens: { a: 1, b: 1 } } }), true)
})

test('nextStatus walks 1->2->3->4->done', () => {
  assert.equal(nextStatus(1), 2)
  assert.equal(nextStatus(2), 3)
  assert.equal(nextStatus(3), 4)
  assert.equal(nextStatus(4), 'done')
  assert.equal(nextStatus('done'), 'done')
})

test('phase1Progress is a 0..1 fraction', () => {
  assert.equal(phase1Progress({ phase1: { total: 0, screens: {} } }), 1)
  assert.equal(phase1Progress({ phase1: { total: 4, screens: { a: 1, b: 1 } } }), 0.5)
})
