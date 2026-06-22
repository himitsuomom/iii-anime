import assert from 'node:assert/strict'
import { test } from 'node:test'
import {
  buildCodebase,
  buildDeployment,
  buildImplementation,
  buildPrd,
  buildScreenAnalysis,
  isSafeRelativePath,
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

test('isSafeRelativePath rejects escapes and absolute paths', () => {
  assert.equal(isSafeRelativePath('src/app.mjs'), true)
  assert.equal(isSafeRelativePath('test.mjs'), true)
  assert.equal(isSafeRelativePath('/etc/passwd'), false)
  assert.equal(isSafeRelativePath('../secret'), false)
  assert.equal(isSafeRelativePath('a/../../b'), false)
  assert.equal(isSafeRelativePath('C:\\win'), false)
  assert.equal(isSafeRelativePath(''), false)
})

test('buildCodebase adopts valid files, drops unsafe, defaults when empty', () => {
  const ok = buildCodebase('Trello', {
    files: [
      { path: 'src/a.mjs', content: 'export const x=1' },
      { path: '../escape.mjs', content: 'bad' }, // dropped
      { path: 'spec.test.mjs', content: 'console.log("TESTS total=1 passed=1 failed=0")' },
    ],
    testFile: 'spec.test.mjs',
  })
  assert.equal(ok.files.length, 2) // unsafe entry filtered out
  assert.equal(ok.testFile, 'spec.test.mjs')

  // No usable files -> runnable default scaffold with a test file.
  const fallback = buildCodebase('Linear', {})
  assert.ok(fallback.files.length >= 1)
  assert.ok(fallback.files.some((f) => f.path === fallback.testFile))

  // Requested testFile that was not materialized -> pick a real one.
  const picked = buildCodebase('X', { files: [{ path: 'main.mjs', content: 'x' }], testFile: 'missing.mjs' })
  assert.equal(picked.testFile, 'main.mjs')
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
