import assert from 'node:assert/strict'
import { describe, test } from 'node:test'
import { LeaderLock, MemoryLockBackend } from './leader.js'

describe('leader election', () => {
  test('only one of two replicas becomes leader', async () => {
    const backend = new MemoryLockBackend()
    const a = new LeaderLock(backend, 'sweep', 'replica-A', 30_000)
    const b = new LeaderLock(backend, 'sweep', 'replica-B', 30_000)
    assert.equal(await a.tryBecomeLeader(), true)
    assert.equal(await b.tryBecomeLeader(), false) // A holds it
    assert.equal(await a.tryBecomeLeader(), true) // A renews
  })

  test('leadership fails over after the lease expires', async () => {
    let now = 1000
    const backend = new MemoryLockBackend(() => now)
    const a = new LeaderLock(backend, 'sweep', 'A', 5_000)
    const b = new LeaderLock(backend, 'sweep', 'B', 5_000)
    assert.equal(await a.tryBecomeLeader(), true)
    assert.equal(await b.tryBecomeLeader(), false)
    now += 6_000 // A's lease expires (A stopped renewing — crashed)
    assert.equal(await b.tryBecomeLeader(), true) // B takes over
    assert.equal(await a.tryBecomeLeader(), false) // A is no longer leader
  })

  test('resign releases leadership', async () => {
    const backend = new MemoryLockBackend()
    const a = new LeaderLock(backend, 'k', 'A', 30_000)
    const b = new LeaderLock(backend, 'k', 'B', 30_000)
    assert.equal(await a.tryBecomeLeader(), true)
    await a.resign()
    assert.equal(await b.tryBecomeLeader(), true)
  })
})
