// Execution runners for the sandbox. The default DirectRunner spawns the command
// as-is (allowlist + workdir confinement are the boundary). IsolatedRunner adds
// kernel namespaces via `unshare` — new mount/uts/ipc/pid namespaces, an
// unprivileged user namespace (map-root, so workdir stays writable but the
// process holds no real host privilege), and (optionally) no network. Opt in
// with STUDIO_SANDBOX_ISOLATION=unshare; falls back to direct if unavailable.
import { spawn, spawnSync } from 'node:child_process'

export interface RunSpec {
  file: string
  args: string[]
  cwd: string
  timeoutMs: number
  env: NodeJS.ProcessEnv
}

export interface RunResult {
  stdout: string
  stderr: string
  exit_code: number
  timed_out: boolean
}

export interface Runner {
  readonly id: string
  run(spec: RunSpec): Promise<RunResult>
}

const MAX_OUTPUT_BYTES = 1_000_000

export class DirectRunner implements Runner {
  readonly id = 'direct'
  run(spec: RunSpec): Promise<RunResult> {
    return spawnCollect(spec.file, spec.args, spec)
  }
}

export interface IsolationOptions {
  /** Allow network access (skip the network namespace). Default false. */
  network?: boolean
}

export class IsolatedRunner implements Runner {
  readonly id = 'unshare'
  constructor(private opts: IsolationOptions = {}) {}
  run(spec: RunSpec): Promise<RunResult> {
    const args = unshareArgs(spec.file, spec.args, { network: this.opts.network ?? false })
    return spawnCollect('unshare', args, spec)
  }
}

/** Build the `unshare` argv that wraps a command in isolation namespaces. */
export function unshareArgs(
  file: string,
  args: string[],
  opts: { network: boolean },
): string[] {
  const flags = ['--user', '--map-root-user', '--mount', '--uts', '--ipc', '--pid', '--fork']
  if (!opts.network) flags.push('--net')
  return [...flags, file, ...args]
}

let unshareChecked: boolean | undefined
export function hasUnshare(): boolean {
  if (unshareChecked === undefined) {
    try {
      unshareChecked = spawnSync('unshare', ['--user', '--map-root-user', 'true']).status === 0
    } catch {
      unshareChecked = false
    }
  }
  return unshareChecked
}

/** Select the runner from env (default direct; unshare with graceful fallback). */
export function makeRunner(): Runner {
  const mode = process.env.STUDIO_SANDBOX_ISOLATION ?? 'direct'
  if (mode === 'unshare') {
    if (hasUnshare()) return new IsolatedRunner({ network: process.env.STUDIO_SANDBOX_NET === '1' })
    // eslint-disable-next-line no-console
    console.warn('[sandbox] STUDIO_SANDBOX_ISOLATION=unshare but unshare is unavailable; using direct')
  }
  return new DirectRunner()
}

function spawnCollect(file: string, args: string[], spec: RunSpec): Promise<RunResult> {
  return new Promise<RunResult>((resolve) => {
    const child = spawn(file, args, { cwd: spec.cwd, env: spec.env, stdio: ['ignore', 'pipe', 'pipe'] })
    let stdout = ''
    let stderr = ''
    let timedOut = false
    let settled = false
    const cap = (buf: string, chunk: Buffer): string =>
      buf.length >= MAX_OUTPUT_BYTES ? buf : buf + chunk.toString('utf8')
    child.stdout.on('data', (c: Buffer) => (stdout = cap(stdout, c)))
    child.stderr.on('data', (c: Buffer) => (stderr = cap(stderr, c)))
    const timer = setTimeout(() => {
      timedOut = true
      child.kill('SIGKILL')
    }, spec.timeoutMs)
    const finish = (exit_code: number) => {
      if (settled) return
      settled = true
      clearTimeout(timer)
      resolve({ stdout, stderr, exit_code, timed_out: timedOut })
    }
    child.on('error', (err) => {
      stderr = cap(stderr, Buffer.from(String(err)))
      finish(127)
    })
    child.on('close', (code, signal) => finish(code ?? (signal ? 137 : 1)))
  })
}
