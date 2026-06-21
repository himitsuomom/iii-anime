import assert from 'node:assert/strict'
import { mkdtemp, rm } from 'node:fs/promises'
import os from 'node:os'
import path from 'node:path'
import { afterEach, beforeEach, describe, test } from 'node:test'
import { DirectRunner, IsolatedRunner, hasUnshare, makeRunner, unshareArgs } from './runner.js'

describe('unshareArgs', () => {
  test('isolates namespaces and drops network by default', () => {
    const a = unshareArgs('node', ['--check', 'x.js'], { network: false })
    assert.deepEqual(a, [
      '--user', '--map-root-user', '--mount', '--uts', '--ipc', '--pid', '--fork', '--net',
      'node', '--check', 'x.js',
    ])
  })
  test('keeps network when requested (no --net)', () => {
    const a = unshareArgs('pnpm', ['install'], { network: true })
    assert.ok(!a.includes('--net'))
    assert.deepEqual(a.slice(-2), ['pnpm', 'install'])
  })
})

describe('makeRunner', () => {
  afterEach(() => {
    delete process.env.STUDIO_SANDBOX_ISOLATION
  })
  test('defaults to the direct runner', () => {
    assert.equal(makeRunner().id, 'direct')
  })
  test('uses unshare when requested and available, else falls back', () => {
    process.env.STUDIO_SANDBOX_ISOLATION = 'unshare'
    assert.equal(makeRunner().id, hasUnshare() ? 'unshare' : 'direct')
  })
})

describe('runners execute commands', () => {
  let cwd: string
  beforeEach(async () => {
    cwd = await mkdtemp(path.join(os.tmpdir(), 'studio-runner-'))
  })
  afterEach(async () => {
    await rm(cwd, { recursive: true, force: true })
  })
  const spec = (file: string, args: string[]) => ({
    file,
    args,
    cwd,
    timeoutMs: 30_000,
    env: { PATH: process.env.PATH ?? '' },
  })

  test('DirectRunner runs a command', async () => {
    const r = await new DirectRunner().run(spec('echo', ['hi']))
    assert.equal(r.exit_code, 0)
    assert.equal(r.stdout.trim(), 'hi')
  })

  test('IsolatedRunner runs a command in namespaces', {
    skip: hasUnshare() ? false : 'unshare unavailable',
  }, async () => {
    const r = await new IsolatedRunner({ network: false }).run(spec('echo', ['iso']))
    assert.equal(r.exit_code, 0)
    assert.equal(r.stdout.trim(), 'iso')
  })
})
