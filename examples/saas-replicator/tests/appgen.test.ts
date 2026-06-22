import assert from 'node:assert/strict'
import { execFile } from 'node:child_process'
import { test } from 'node:test'
import { promisify } from 'node:util'
import { synthesizeApp } from '../src/logic/appgen'
import { parseTestStdout } from '../src/logic/artifacts'
import { cleanup, createWorkspace, materialize } from '../src/workspace'

const run = promisify(execFile)

test('synthesizeApp produces a model per entity, an api, an app, and a test', () => {
  const cb = synthesizeApp('Trello', { features: ['boards', 'cards'], dataModel: ['users', 'boards', 'cards'] })
  const paths = cb.files.map((f) => f.path)
  assert.ok(paths.includes('src/models/users.mjs'))
  assert.ok(paths.includes('src/models/boards.mjs'))
  assert.ok(paths.includes('src/api.mjs'))
  assert.ok(paths.includes('src/app.mjs'))
  assert.equal(cb.testFile, 'test.mjs')
  // 3 models + api + app + test = 6 files.
  assert.equal(cb.files.length, 6)
  // All paths are safe relatives.
  assert.ok(cb.files.every((f) => !f.path.startsWith('/') && !f.path.includes('..')))
})

test('synthesizeApp defaults to one model + health api when PRD is empty', () => {
  const cb = synthesizeApp('X', { features: [], dataModel: [] })
  assert.ok(cb.files.some((f) => f.path === 'src/models/item.mjs'))
  assert.ok(cb.files.some((f) => f.path === 'src/api.mjs'))
})

test('the synthesized app actually runs and all generated cases pass', async () => {
  const cb = synthesizeApp('Trello', { features: ['boards', 'cards'], dataModel: ['users', 'boards'] })
  const root = await createWorkspace('saas-appgen-')
  try {
    await materialize(cb.files, root)
    const { stdout } = await run(process.execPath, [cb.testFile], { cwd: root })
    const report = parseTestStdout(stdout, false)
    assert.ok(report.total > 2, 'multiple generated assertions')
    assert.equal(report.failed, 0, 'every generated assertion passes')
  } finally {
    await cleanup(root)
  }
})
