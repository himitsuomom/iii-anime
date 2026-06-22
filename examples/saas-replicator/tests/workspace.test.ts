import assert from 'node:assert/strict'
import { readFile, stat } from 'node:fs/promises'
import { join } from 'node:path'
import { test } from 'node:test'
import { cleanup, createWorkspace, materialize } from '../src/workspace'

test('materialize writes files (incl. nested dirs), skips unsafe, cleanup removes', async () => {
  const root = await createWorkspace('saas-test-')
  try {
    const written = await materialize(
      [
        { path: 'src/app.mjs', content: 'export const x = 1\n' },
        { path: 'test.mjs', content: 'console.log("ok")\n' },
        { path: '../escape.mjs', content: 'nope' }, // unsafe -> skipped
      ],
      root,
    )

    assert.deepEqual(written.sort(), ['src/app.mjs', 'test.mjs'])
    assert.equal(await readFile(join(root, 'src/app.mjs'), 'utf8'), 'export const x = 1\n')
  } finally {
    await cleanup(root)
  }
  // Directory is gone after cleanup.
  await assert.rejects(() => stat(root))
})
