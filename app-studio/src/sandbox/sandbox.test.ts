import assert from 'node:assert/strict'
import { mkdtemp, rm, writeFile, mkdir, symlink } from 'node:fs/promises'
import os from 'node:os'
import path from 'node:path'
import { afterEach, beforeEach, describe, test } from 'node:test'
import { parseCommand, SandboxCommandError } from './allowlist.js'
import { editInWorkspace } from './edit.js'
import { execInWorkspace } from './exec.js'
import { resolveInside, SandboxPathError, workspaceDir } from './workspace.js'

const PID = 'prj_test'
let base: string

beforeEach(async () => {
  base = await mkdtemp(path.join(os.tmpdir(), 'studio-test-'))
  process.env.STUDIO_WORK_ROOT = base
})
afterEach(async () => {
  await rm(base, { recursive: true, force: true })
  delete process.env.STUDIO_WORK_ROOT
})

describe('allowlist', () => {
  test('accepts an allowlisted command', () => {
    assert.deepEqual(parseCommand('pnpm test'), { file: 'pnpm', args: ['test'] })
  })
  test('rejects shell operators', () => {
    for (const cmd of ['rm -rf / && echo hi', 'cat a | sh', 'echo `id`', 'echo $(id)', 'a; b']) {
      assert.throws(() => parseCommand(cmd), SandboxCommandError, cmd)
    }
  })
  test('rejects non-allowlisted executables', () => {
    assert.throws(() => parseCommand('curl http://evil'), SandboxCommandError)
    assert.throws(() => parseCommand('bash -c whoami'), SandboxCommandError)
  })
  test('honors quotes when tokenizing', () => {
    assert.deepEqual(parseCommand('echo "hello world"'), { file: 'echo', args: ['hello world'] })
  })
})

describe('workspace confinement', () => {
  test('rejects parent-escape and absolute paths', async () => {
    await assert.rejects(() => resolveInside(PID, '../escape'), SandboxPathError)
    await assert.rejects(() => resolveInside(PID, '/etc/passwd'), SandboxPathError)
    await assert.rejects(() => resolveInside(PID, 'a/../../b'), SandboxPathError)
  })
  test('allows nested in-workspace paths', async () => {
    const p = await resolveInside(PID, 'src/app.ts')
    assert.ok(p.startsWith(workspaceDir(PID)))
  })
  test('rejects symlink that escapes the workspace', async () => {
    const dir = workspaceDir(PID)
    await mkdir(dir, { recursive: true })
    const outside = await mkdtemp(path.join(os.tmpdir(), 'outside-'))
    await symlink(outside, path.join(dir, 'link'))
    await assert.rejects(() => resolveInside(PID, 'link/secret.txt'), SandboxPathError)
    await rm(outside, { recursive: true, force: true })
  })
})

describe('exec', () => {
  test('runs an allowlisted command and captures output', async () => {
    const r = await execInWorkspace({ project_id: PID, cmd: 'echo hello' })
    assert.equal(r.exit_code, 0)
    assert.equal(r.timed_out, false)
    assert.equal(r.stdout.trim(), 'hello')
  })
  test('reports non-zero exit codes', async () => {
    const r = await execInWorkspace({ project_id: PID, cmd: 'test -f does-not-exist' })
    assert.notEqual(r.exit_code, 0)
  })
  test('rejects disallowed commands before spawning', async () => {
    await assert.rejects(
      () => execInWorkspace({ project_id: PID, cmd: 'curl http://evil' }),
      SandboxCommandError,
    )
  })
  test('enforces a timeout', async () => {
    // A sleeper script keeps the event loop alive; the hard timeout must kill it.
    await editInWorkspace({
      project_id: PID,
      command: 'create',
      path: 'sleep.js',
      file_text: 'setTimeout(function () {}, 10000)\n',
    })
    const r = await execInWorkspace({ project_id: PID, cmd: 'node sleep.js', timeout_ms: 200 })
    assert.equal(r.timed_out, true)
  })
  test('runs in the project workspace cwd', async () => {
    await execInWorkspace({ project_id: PID, cmd: 'mkdir sub' })
    const r = await execInWorkspace({ project_id: PID, cmd: 'ls' })
    assert.ok(r.stdout.includes('sub'))
  })
})

describe('edit', () => {
  test('create then view round-trips', async () => {
    const c = await editInWorkspace({
      project_id: PID,
      command: 'create',
      path: 'src/index.ts',
      file_text: 'export const x = 1\n',
    })
    assert.equal(c.ok, true)
    const v = await editInWorkspace({ project_id: PID, command: 'view', path: 'src/index.ts' })
    assert.equal(v.content, 'export const x = 1\n')
  })
  test('str_replace requires a unique match', async () => {
    await editInWorkspace({ project_id: PID, command: 'create', path: 'f.txt', file_text: 'a\na\n' })
    const dup = await editInWorkspace({
      project_id: PID,
      command: 'str_replace',
      path: 'f.txt',
      old_str: 'a',
      new_str: 'b',
    })
    assert.equal(dup.ok, false)
    assert.match(dup.error ?? '', /2 times/)

    await editInWorkspace({ project_id: PID, command: 'create', path: 'g.txt', file_text: 'foo\n' })
    const ok = await editInWorkspace({
      project_id: PID,
      command: 'str_replace',
      path: 'g.txt',
      old_str: 'foo',
      new_str: 'bar',
    })
    assert.equal(ok.ok, true)
    const v = await editInWorkspace({ project_id: PID, command: 'view', path: 'g.txt' })
    assert.equal(v.content, 'bar\n')
  })
  test('insert places text after the given line', async () => {
    await editInWorkspace({ project_id: PID, command: 'create', path: 'h.txt', file_text: 'l1\nl2\n' })
    await editInWorkspace({
      project_id: PID,
      command: 'insert',
      path: 'h.txt',
      insert_line: 1,
      insert_text: 'INSERTED',
    })
    const v = await editInWorkspace({ project_id: PID, command: 'view', path: 'h.txt' })
    assert.equal(v.content, 'l1\nINSERTED\nl2\n')
  })
  test('refuses to write outside the workspace', async () => {
    const r = await editInWorkspace({
      project_id: PID,
      command: 'create',
      path: '../escape.txt',
      file_text: 'x',
    })
    assert.equal(r.ok, false)
    assert.match(r.error ?? '', /escapes workspace/)
  })
})
