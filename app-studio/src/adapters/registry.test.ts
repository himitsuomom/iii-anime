import assert from 'node:assert/strict'
import { describe, test } from 'node:test'
import type { Plan } from '../types.js'
import { adapterIds, designGuidanceBlock, getAdapter, rubricFor } from './registry.js'

const plan = (over: Partial<Plan>): Plan => ({
  app_type: 'web-node',
  stack: ['node'],
  tasks: [],
  build_cmd: 'node --check server.js',
  test_cmd: 'node --test',
  ...over,
})

describe('adapter registry', () => {
  test('registers the built-in adapters', () => {
    assert.deepEqual(adapterIds().sort(), ['static-web', 'web-node'])
    assert.ok(getAdapter('web-node'))
    assert.equal(getAdapter('nope'), undefined)
  })

  test('web-node rubric uses the plan build/test commands', () => {
    const r = rubricFor(plan({}))
    assert.deepEqual(
      r.hard.map((h) => h.cmd),
      ['node --check server.js', 'node --test'],
    )
  })

  test('static-web rubric asserts index.html and the test command', () => {
    const r = rubricFor(plan({ app_type: 'static-web', build_cmd: 'true' }))
    assert.deepEqual(
      r.hard.map((h) => h.id),
      ['index', 'test'],
    )
    assert.equal(r.hard[0]!.cmd, 'test -f index.html')
  })

  test('unknown app_type falls back to build/test commands', () => {
    const r = rubricFor(plan({ app_type: 'mystery' }))
    assert.equal(r.hard.length, 2)
  })

  test('design guidance block lists every adapter', () => {
    const block = designGuidanceBlock()
    for (const id of adapterIds()) assert.ok(block.includes(`"${id}"`))
  })
})
