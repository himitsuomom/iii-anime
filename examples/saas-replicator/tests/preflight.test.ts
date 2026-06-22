import assert from 'node:assert/strict'
import { test } from 'node:test'
import { buildPreflightReport } from '../src/logic/preflight'

test('stub mode is always ok and needs no key/workers', () => {
  const r = buildPreflightReport({ mode: 'stub', hasAnthropicKey: false, workers: [] })
  assert.equal(r.ok, true)
  assert.equal(r.problems.length, 0)
  assert.ok(r.notes.some((n) => n.includes('stub mode')))
})

test('live mode flags missing provider-anthropic and missing API key', () => {
  const r = buildPreflightReport({ mode: 'live', hasAnthropicKey: false, workers: [] })
  assert.equal(r.ok, false)
  assert.ok(r.problems.some((p) => p.includes('provider-anthropic')))
  assert.ok(r.problems.some((p) => p.includes('ANTHROPIC_API_KEY')))
})

test('live mode is ok with the provider worker + key; notes reflect optional workers', () => {
  const r = buildPreflightReport({
    mode: 'live',
    hasAnthropicKey: true,
    workers: ['provider-anthropic', 'provider-kimi', 'iii-sandbox', 'approval-gate'],
  })
  assert.equal(r.ok, true)
  assert.ok(r.notes.some((n) => n.includes('debate enabled')))
  assert.ok(r.notes.some((n) => n.includes('microVM')))
})

test('absent optional workers degrade gracefully in notes', () => {
  const r = buildPreflightReport({ mode: 'live', hasAnthropicKey: true, workers: ['provider-anthropic'] })
  assert.equal(r.ok, true)
  assert.ok(r.notes.some((n) => n.includes('self-critique')))
  assert.ok(r.notes.some((n) => n.includes('local child-process executor')))
  assert.ok(r.notes.some((n) => n.includes('auto-approves')))
})
