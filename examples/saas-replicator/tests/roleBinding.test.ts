import assert from 'node:assert/strict'
import { test } from 'node:test'
import { DEFAULT_MODELS, providerFunctionId, resolveBindings, resolveRole } from '../src/logic/roleBinding'

test('default (Claude-only): every role binds to anthropic', () => {
  const b = resolveBindings()
  for (const role of Object.keys(b) as Array<keyof typeof b>) {
    assert.equal(b[role].provider, 'anthropic')
    assert.equal(b[role].functionId, 'provider-anthropic::messages')
    assert.equal(b[role].model, DEFAULT_MODELS.anthropic)
  }
})

test('kimi available: analysis/viz/test/swarm rebind to kimi, director stays anthropic', () => {
  const b = resolveBindings({ kimiAvailable: true })
  assert.equal(b.director.provider, 'anthropic')
  assert.equal(b.analyzer.provider, 'kimi')
  assert.equal(b.visualizer.provider, 'kimi')
  assert.equal(b.tester.provider, 'kimi')
  assert.equal(b.swarm.provider, 'kimi')
})

test('stub mode forces every role onto the stub provider', () => {
  const b = resolveBindings({ mode: 'stub', kimiAvailable: true })
  for (const role of Object.keys(b) as Array<keyof typeof b>) {
    assert.equal(b[role].provider, 'stub')
    assert.equal(b[role].functionId, 'saas::provider::stub')
  }
})

test('explicit override beats kimi auto-binding', () => {
  const b = resolveBindings({ kimiAvailable: true, overrides: { analyzer: 'anthropic' } })
  assert.equal(b.analyzer.provider, 'anthropic')
  assert.equal(b.visualizer.provider, 'kimi')
})

test('resolveRole returns a single binding and providerFunctionId is correct', () => {
  assert.equal(resolveRole('director').provider, 'anthropic')
  assert.equal(providerFunctionId('kimi'), 'provider-kimi::messages')
})
