// sandbox::exec — run one allowlisted command inside a project's workdir.
// No shell, hard timeout, minimal env, cwd confined to the workspace. Execution
// is delegated to a Runner (direct, or unshare-isolated) — see runner.ts.
import { DEFAULT_ALLOWLIST, parseCommand } from './allowlist.js'
import { makeRunner, type Runner } from './runner.js'
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

let runner: Runner | undefined
function getRunner(): Runner {
  if (!runner) runner = makeRunner()
  return runner
}

export async function execInWorkspace(input: ExecInput): Promise<ExecResult> {
  const { project_id, cmd } = input
  const { file, args } = parseCommand(cmd, input.allowlist ?? DEFAULT_ALLOWLIST)

  await ensureWorkspace(project_id)
  const root = workspaceDir(project_id)
  const cwd = input.cwd ? await resolveInside(project_id, input.cwd) : root
  const timeoutMs = input.timeout_ms ?? DEFAULT_TIMEOUT_MS

  return getRunner().run({
    file,
    args,
    cwd,
    timeoutMs,
    env: { PATH: process.env.PATH ?? '', HOME: root, CI: '1' },
  })
}
