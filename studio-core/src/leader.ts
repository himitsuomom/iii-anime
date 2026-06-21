// Leader election for HA. When >1 factory worker replica runs against one
// engine, exactly one should perform singleton work (the resume/sweep cron).
// A short-TTL lock with periodic re-acquire gives leadership + automatic
// failover. Backends: MemoryLockBackend (tests/single-process) and
// RedisCliLockBackend (production, shells out to redis-cli — no extra dep).
import { spawn } from 'node:child_process'

export interface LockBackend {
  /** Acquire or renew leadership of `key` for `holder`. True if held after the call. */
  tryAcquire(key: string, holder: string, ttlMs: number): Promise<boolean>
  release(key: string, holder: string): Promise<void>
}

export class MemoryLockBackend implements LockBackend {
  private held = new Map<string, { holder: string; exp: number }>()
  constructor(private now: () => number = () => Date.now()) {}

  async tryAcquire(key: string, holder: string, ttlMs: number): Promise<boolean> {
    const t = this.now()
    const cur = this.held.get(key)
    if (cur && cur.exp > t && cur.holder !== holder) return false // someone else holds it
    this.held.set(key, { holder, exp: t + ttlMs })
    return true
  }
  async release(key: string, holder: string): Promise<void> {
    const cur = this.held.get(key)
    if (cur && cur.holder === holder) this.held.delete(key)
  }
}

export class RedisCliLockBackend implements LockBackend {
  constructor(
    private url: string,
    private bin = 'redis-cli',
  ) {}

  async tryAcquire(key: string, holder: string, ttlMs: number): Promise<boolean> {
    // Acquire if free (NX). If we already hold it, renew the TTL.
    const set = (await this.cli(['set', key, holder, 'NX', 'PX', String(ttlMs)])).trim()
    if (set === 'OK') return true
    const cur = (await this.cli(['get', key])).trim()
    if (cur === holder) {
      await this.cli(['set', key, holder, 'PX', String(ttlMs)]) // renew (we own it)
      return true
    }
    return false
  }
  async release(key: string, holder: string): Promise<void> {
    const cur = (await this.cli(['get', key])).trim()
    if (cur === holder) await this.cli(['del', key])
  }
  private cli(args: string[]): Promise<string> {
    return new Promise((resolve) => {
      const child = spawn(this.bin, ['-u', this.url, ...args])
      let out = ''
      child.stdout.on('data', (c: Buffer) => (out += c.toString('utf8')))
      child.on('error', () => resolve(''))
      child.on('close', () => resolve(out))
    })
  }
}

export class LeaderLock {
  constructor(
    private backend: LockBackend,
    private key: string,
    private holder: string,
    private ttlMs = 30_000,
  ) {}
  /** True if this replica is (now) the leader. Call before doing singleton work. */
  tryBecomeLeader(): Promise<boolean> {
    return this.backend.tryAcquire(this.key, this.holder, this.ttlMs)
  }
  resign(): Promise<void> {
    return this.backend.release(this.key, this.holder)
  }
}
