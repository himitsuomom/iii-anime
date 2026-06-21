// ClaudeCodeBackend — drive the local Claude Code CLI headlessly to build the
// app. Claude Code brings its own bash/edit/write tools, sandbox, and
// generate->test->fix loop, and uses the machine's existing Claude Code login
// (no ANTHROPIC_API_KEY needed; subscription auth works). We run it scoped to
// the project workdir and parse its JSON result.
import { spawn } from 'node:child_process'
import { assetArgs, assetsFromEnv, type ClaudeAssets } from '../../../studio-core/src/assets.js'
import type { BuildBackend, BuildOutcome, BuildRequest } from './backend.js'

export interface ClaudeCodeOptions {
  /** Path/name of the Claude Code binary. */
  bin?: string
  /** Tools the build agent may use, unattended (no prompts). */
  allowedTools?: string[]
  /**
   * Permission handling for unattended runs. 'acceptEdits' auto-accepts file
   * edits; combine with allowedTools to pre-approve Bash. 'skip' passes
   * --dangerously-skip-permissions (only safe inside an isolated sandbox/container).
   */
  permission?: 'acceptEdits' | 'skip'
  /** Extra args appended verbatim (escape hatch). */
  extraArgs?: string[]
  /** Overall wall-clock timeout for one build. */
  timeoutMs?: number
  /** Existing Claude assets (MCP/skills/plugins/...) to give the agent. */
  assets?: ClaudeAssets
}

const DEFAULT_TOOLS = ['Bash', 'Edit', 'Write', 'Read', 'Glob', 'Grep']

export class ClaudeCodeBackend implements BuildBackend {
  readonly id = 'claude-code'
  private opts: Required<Omit<ClaudeCodeOptions, 'extraArgs' | 'assets'>> &
    Pick<ClaudeCodeOptions, 'extraArgs'> & { assets: ClaudeAssets }

  constructor(opts: ClaudeCodeOptions = {}) {
    this.opts = {
      bin: opts.bin ?? 'claude',
      allowedTools: opts.allowedTools ?? DEFAULT_TOOLS,
      permission: opts.permission ?? 'acceptEdits',
      timeoutMs: opts.timeoutMs ?? 30 * 60_000,
      extraArgs: opts.extraArgs,
      assets: opts.assets ?? assetsFromEnv(),
    }
  }

  async run(req: BuildRequest): Promise<BuildOutcome> {
    // Merge any asset-provided tools into one --allowedTools (the user's MCP
    // tools, extra skills, etc.), then add the rest of the asset flags.
    const tools = [...this.opts.allowedTools, ...(this.opts.assets.allowedTools ?? [])]
    const args = [
      '-p',
      req.userPrompt,
      '--append-system-prompt',
      req.systemPrompt,
      '--output-format',
      'json',
      '--max-turns',
      String(req.maxTurns ?? 60),
      '--allowedTools',
      ...tools,
    ]
    if (this.opts.permission === 'skip') args.push('--dangerously-skip-permissions')
    else args.push('--permission-mode', 'acceptEdits')
    args.push(...assetArgs({ ...this.opts.assets, allowedTools: undefined }))
    if (this.opts.extraArgs) args.push(...this.opts.extraArgs)

    const { code, stdout, stderr, timedOut } = await this.spawn(args, req.workdir)
    if (timedOut) return { ok: false, summary: '', error: 'build timed out' }

    const json = parseLastJson(stdout)
    if (!json) {
      return { ok: false, summary: '', error: `no JSON result (exit ${code}): ${stderr.slice(0, 500)}` }
    }
    const ok = json.subtype === 'success' && json.is_error !== true
    return {
      ok,
      summary: typeof json.result === 'string' ? json.result : '',
      num_turns: json.num_turns,
      cost_usd: json.total_cost_usd,
      session_id: json.session_id,
      error: ok ? undefined : (json.subtype ?? 'build failed'),
      raw: json,
    }
  }

  private spawn(
    args: string[],
    cwd: string,
  ): Promise<{ code: number; stdout: string; stderr: string; timedOut: boolean }> {
    return new Promise((resolve) => {
      const child = spawn(this.opts.bin, args, { cwd, env: process.env })
      let stdout = ''
      let stderr = ''
      let timedOut = false
      const timer = setTimeout(() => {
        timedOut = true
        child.kill('SIGKILL')
      }, this.opts.timeoutMs)
      child.stdout.on('data', (c: Buffer) => (stdout += c.toString('utf8')))
      child.stderr.on('data', (c: Buffer) => (stderr += c.toString('utf8')))
      child.on('error', (e) => {
        clearTimeout(timer)
        resolve({ code: 127, stdout, stderr: stderr + String(e), timedOut })
      })
      child.on('close', (code) => {
        clearTimeout(timer)
        resolve({ code: code ?? 1, stdout, stderr, timedOut })
      })
    })
  }
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function parseLastJson(s: string): any | null {
  const trimmed = s.trim()
  if (!trimmed) return null
  try {
    return JSON.parse(trimmed)
  } catch {
    // Fall back to the last JSON line (in case extra logging precedes it).
    const lines = trimmed.split('\n').reverse()
    for (const line of lines) {
      try {
        return JSON.parse(line)
      } catch {
        /* keep scanning */
      }
    }
    return null
  }
}
