// sandbox::exec — run one allowlisted command inside a project's workdir.
// No shell, hard timeout, minimal env, cwd confined to the workspace.
import { spawn } from 'node:child_process'
import { DEFAULT_ALLOWLIST, parseCommand } from './allowlist.js'
import { ensureWorkspace, resolveInside, workspaceDir } from './workspace.js'

export interface ExecInput {
  project_id: string
  cmd: string
  /** workdir-relative cwd; defaults to the workspace root. */
  cwd?: string
  timeout_ms?: number
  allowlist?: ReadonlySet<string>
}

export interface ExecResult {
  stdout: string
  stderr: string
  exit_code: number
  timed_out: boolean
}

const DEFAULT_TIMEOUT_MS = 120_000
const MAX_OUTPUT_BYTES = 1_000_000 // cap captured output to avoid blowing up context

export async function execInWorkspace(input: ExecInput): Promise<ExecResult> {
  const { project_id, cmd } = input
  const { file, args } = parseCommand(cmd, input.allowlist ?? DEFAULT_ALLOWLIST)

  await ensureWorkspace(project_id)
  const root = workspaceDir(project_id)
  const cwd = input.cwd ? await resolveInside(project_id, input.cwd) : root
  const timeoutMs = input.timeout_ms ?? DEFAULT_TIMEOUT_MS

  return await new Promise<ExecResult>((resolve) => {
    const child = spawn(file, args, {
      cwd,
      env: { PATH: process.env.PATH ?? '', HOME: root, CI: '1' },
      stdio: ['ignore', 'pipe', 'pipe'],
    })

    let stdout = ''
    let stderr = ''
    let timedOut = false
    let settled = false

    const cap = (buf: string, chunk: Buffer): string =>
      buf.length >= MAX_OUTPUT_BYTES ? buf : buf + chunk.toString('utf8')

    child.stdout.on('data', (c: Buffer) => {
      stdout = cap(stdout, c)
    })
    child.stderr.on('data', (c: Buffer) => {
      stderr = cap(stderr, c)
    })

    const timer = setTimeout(() => {
      timedOut = true
      child.kill('SIGKILL')
    }, timeoutMs)

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
    child.on('close', (code, signal) => {
      finish(code ?? (signal ? 137 : 1))
    })
  })
}
