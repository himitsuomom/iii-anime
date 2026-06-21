import assert from 'node:assert/strict'
import { test } from 'node:test'
import {
  buildDeployment,
  buildImplementation,
  buildPrd,
  buildScreenAnalysis,
  parseJsonFromContent,
  parseTestStdout,
} from '../src/logic/artifacts'

test('parseJsonFromContent: raw object, provider {content}, JSON string, fenced, embedded', () => {
  assert.deepEqual(parseJsonFromContent({ a: 1 }), { a: 1 })
  assert.deepEqual(parseJsonFromContent({ content: '{"a":1}' }), { a: 1 })
  assert.deepEqual(parseJsonFromContent('{"a":1}'), { a: 1 })
  assert.deepEqual(parseJsonFromContent('```json\n{"a":1}\n```'), { a: 1 })
  assert.deepEqual(parseJsonFromContent('noise {"a":1} tail'), { a: 1 })
  assert.deepEqual(parseJsonFromContent('not json at all'), {})
})

test('builders fill defaults for missing fields', () => {
  const tokens = buildScreenAnalysis('board', {})
  assert.equal(tokens.screen, 'board')
  assert.deepEqual(tokens.components, [])
  assert.deepEqual(tokens.tokens, { colors: [], fonts: [], spacing: [] })

  const prd = buildPrd('Trello', {})
  assert.equal(prd.target, 'Trello')
  assert.ok(prd.summary.length > 0)

  const impl = buildImplementation('Trello', {})
  assert.ok(impl.files.length >= 2) // default file plan

  const dep = buildDeployment({})
  assert.equal(dep.pwa, true)
  assert.ok(dep.url.startsWith('http'))
})

test('builders pass through provided values', () => {
  const a = buildScreenAnalysis('card', {
    components: ['Button'],
    tokens: { colors: ['#fff'], fonts: ['Inter'], spacing: [4, 8] },
  })
  assert.deepEqual(a.components, ['Button'])
  assert.deepEqual(a.tokens.spacing, [4, 8])

  const prd = buildPrd('X', { summary: 's', features: ['f'], dataModel: ['users'] })
  assert.deepEqual(prd.features, ['f'])
})

test('parseTestStdout extracts counts from a summary line', () => {
  const r = parseTestStdout('noise\nTESTS total=5 passed=4 failed=1\nmore', true)
  assert.deepEqual(r, {
    total: 5,
    passed: 4,
    failed: 1,
    viaSandbox: true,
    stdout: 'noise\nTESTS total=5 passed=4 failed=1\nmore',
  })

  const empty = parseTestStdout('no summary', false)
  assert.equal(empty.total, 0)
  assert.equal(empty.viaSandbox, false)
})
