// ClaudeCliBrain — structured generation via the local Claude Code CLI.
// Runs `claude -p` headless (no API key; uses existing Claude Code login),
// asks for JSON only, and validates the parsed result. Used by intake/design.
import { spawn } from 'node:child_process'
import type { Brain, JsonRequest, TextRequest } from './brain.js'

export interface ClaudeCliBrainOptions {
  bin?: string
  timeoutMs?: number
}

export class ClaudeCliBrain implements Brain {
  readonly id = 'claude-cli'
  private bin: string
  private timeoutMs: number

  constructor(opts: ClaudeCliBrainOptions = {}) {
    this.bin = opts.bin ?? 'claude'
    this.timeoutMs = opts.timeoutMs ?? 5 * 60_000
  }

  async json<T>(req: JsonRequest<T>): Promise<T> {
    const system = `${req.system}\n\nRespond with ONLY a single JSON object that matches the requested shape. No prose, no markdown, no code fences.`
    const args = [
      '-p',
      req.user,
      '--append-system-prompt',
      system,
      '--output-format',
      'json',
      '--max-turns',
      String(req.maxTurns ?? 2),
    ]
    const { stdout, stderr, code } = await this.spawn(args)
    const envelope = parseJson(stdout)
    if (!envelope || typeof envelope.result !== 'string') {
      throw new Error(`claude returned no result (exit ${code}): ${stderr.slice(0, 300)}`)
    }
    const parsed = parseJson(stripFences(envelope.result))
    if (parsed === null) throw new Error(`model output was not JSON: ${envelope.result.slice(0, 300)}`)
    return req.validate(parsed)
  }

  async text(req: TextRequest): Promise<string> {
    const args = [
      '-p',
      req.user,
      '--append-system-prompt',
      req.system,
      '--output-format',
      'json',
      '--max-turns',
      String(req.maxTurns ?? 2),
    ]
    const { stdout, stderr, code } = await this.spawn(args)
    const envelope = parseJson(stdout)
    if (!envelope || typeof envelope.result !== 'string') {
      throw new Error(`claude returned no result (exit ${code}): ${stderr.slice(0, 300)}`)
    }
    return envelope.result
  }

  private spawn(args: string[]): Promise<{ stdout: string; stderr: string; code: number }> {
    return new Promise((resolve) => {
      const child = spawn(this.bin, args, { env: process.env })
      let stdout = ''
      let stderr = ''
      const timer = setTimeout(() => child.kill('SIGKILL'), this.timeoutMs)
      child.stdout.on('data', (c: Buffer) => (stdout += c.toString('utf8')))
      child.stderr.on('data', (c: Buffer) => (stderr += c.toString('utf8')))
      child.on('error', (e) => {
        clearTimeout(timer)
        resolve({ stdout, stderr: stderr + String(e), code: 127 })
      })
      child.on('close', (code) => {
        clearTimeout(timer)
        resolve({ stdout, stderr, code: code ?? 1 })
      })
    })
  }
}

function stripFences(s: string): string {
  return s
    .trim()
    .replace(/^```(?:json)?\s*/i, '')
    .replace(/\s*```$/, '')
    .trim()
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function parseJson(s: string): any | null {
  try {
    return JSON.parse(s.trim())
  } catch {
    return null
  }
}
