import assert from 'node:assert/strict'
import { describe, test } from 'node:test'
import { projectIdFromKey, randomProjectId } from './idempotency.js'
import { MemoryKvStore } from './store.js'

interface Doc {
  id: string
  n: number
  rev?: number
}

describe('MemoryKvStore', () => {
  const make = () =>
    new MemoryKvStore<Doc>(
      (d) => d.id,
      (d) => ({ ...d, rev: (d.rev ?? 0) + 1 }), // stamp on update only
    )

  test('set stores as-is (no stamp); get/list', async () => {
    const s = make()
    await s.set({ id: 'a', n: 1 })
    assert.deepEqual(await s.get('a'), { id: 'a', n: 1 })
    assert.equal((await s.list()).length, 1)
    assert.equal(await s.get('missing'), null)
  })

  test('update merges and applies the stamp', async () => {
    const s = make()
    await s.set({ id: 'a', n: 1 })
    const next = await s.update('a', { n: 2 })
    assert.equal(next.n, 2)
    assert.equal(next.rev, 1) // stamp ran on update
    await assert.rejects(() => s.update('missing', { n: 0 }))
  })
})

describe('idempotency (moved into studio-core)', () => {
  test('deterministic id from key, random otherwise', () => {
    assert.equal(projectIdFromKey('x'), projectIdFromKey('x'))
    assert.notEqual(projectIdFromKey('x'), projectIdFromKey('y'))
    assert.match(randomProjectId(), /^prj_/)
  })
})
