/**
 * Code executors for the Phase 3 test run.
 *
 * Two implementations share one interface so the orchestrator does not care
 * where code runs:
 *  - `sandboxExecutor` — isolated microVM via the `iii-sandbox` worker (preferred
 *    in production; generated code must run isolated).
 *  - `localExecutor` — a dev fallback that spawns `node` in a child process in
 *    the materialized workspace. Used when no sandbox worker is present so the
 *    example still actually runs generated tests (e.g. with no /dev/kvm).
 */

import { spawn } from 'node:child_process'
import type { Engine } from './engine'
import { runInSandbox, type SandboxLang, type SandboxResult, sandboxAvailable } from './sandbox'

export interface RunOptions {
  lang: SandboxLang
  /** Relative path of a file in `cwd` to execute (preferred). */
  file?: string
  /** Inline code to execute (used when `file` is absent). */
  code?: string
  /** Working directory (the materialized workspace) for the local executor. */
  cwd?: string
  /** Hard timeout in milliseconds. */
  timeoutMs?: number
}

export interface CodeExecutor {
  readonly kind: 'sandbox' | 'local'
  run(opts: RunOptions): Promise<SandboxResult>
}

/** Runs code in the iii-sandbox microVM. */
export function sandboxExecutor(engine: Engine): CodeExecutor {
  return {
    kind: 'sandbox',
    async run(opts: RunOptions): Promise<SandboxResult> {
      // The sandbox worker takes inline code; callers materialize + read the
      // file, but for the skeleton we pass `code` (or a read of `file`).
      return runInSandbox(engine, { lang: opts.lang, code: opts.code ?? '' })
    },
  }
}

/** Spawns `node <file>` (or `node -e <code>`) locally and captures output. */
export function localExecutor(): CodeExecutor {
  return {
    kind: 'local',
    run(opts: RunOptions): Promise<SandboxResult> {
      const args = opts.file ? [opts.file] : ['-e', opts.code ?? '']
      return spawnCapture(process.execPath, args, opts.cwd, opts.timeoutMs ?? 30_000)
    },
  }
}

/** Pick the sandbox executor when available, else the local child-process one. */
export async function pickExecutor(engine: Engine): Promise<CodeExecutor> {
  return (await sandboxAvailable(engine)) ? sandboxExecutor(engine) : localExecutor()
}

function spawnCapture(cmd: string, args: string[], cwd: string | undefined, timeoutMs: number): Promise<SandboxResult> {
  return new Promise((resolve) => {
    const start = Date.now()
    const child = spawn(cmd, args, { cwd, timeout: timeoutMs })
    let stdout = ''
    let stderr = ''
    child.stdout?.on('data', (d) => {
      stdout += String(d)
    })
    child.stderr?.on('data', (d) => {
      stderr += String(d)
    })
    child.on('error', (err) => {
      resolve({ stdout, stderr: `${stderr}${err}`, exit_code: -1, success: false, duration_ms: Date.now() - start })
    })
    child.on('close', (code, signal) => {
      const exit_code = code ?? -1
      resolve({
        stdout,
        stderr,
        exit_code,
        success: exit_code === 0,
        timed_out: signal === 'SIGTERM',
        duration_ms: Date.now() - start,
      })
    })
  })
}
