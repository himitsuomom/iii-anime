// Command allowlist. A sandbox command is exactly one executable plus args —
// no shell. We reject anything that smells like shell composition so the
// model can't chain its way out via `&&`, pipes, subshells, or redirection.

export class SandboxCommandError extends Error {}

/** Executables the build agent may run in a workdir (web-node P0 set). */
export const DEFAULT_ALLOWLIST: ReadonlySet<string> = new Set([
  'node',
  'pnpm',
  'npm',
  'npx',
  'git',
  'ls',
  'cat',
  'mkdir',
  'rm',
  'mv',
  'cp',
  'sed',
  'grep',
  'find',
  'test',
  'echo',
  'true',
])

// Characters that imply shell metasyntax. A single command must contain none.
const SHELL_METACHARS = /[&|;<>`$()\n\r{}]/

export interface ParsedCommand {
  file: string
  args: string[]
}

/**
 * Parse and validate a single command string. Throws SandboxCommandError if it
 * uses shell composition or an executable outside the allowlist.
 */
export function parseCommand(
  cmd: string,
  allowlist: ReadonlySet<string> = DEFAULT_ALLOWLIST,
): ParsedCommand {
  const trimmed = cmd.trim()
  if (trimmed.length === 0) throw new SandboxCommandError('empty command')
  if (SHELL_METACHARS.test(trimmed)) {
    throw new SandboxCommandError(
      `shell operators are not allowed; run one command per call: ${cmd}`,
    )
  }
  const tokens = tokenize(trimmed)
  const file = tokens[0]!
  if (!allowlist.has(file)) {
    throw new SandboxCommandError(`executable not allowed: ${file}`)
  }
  return { file, args: tokens.slice(1) }
}

/** Split on whitespace, honoring simple single/double quotes (no shell expansion). */
function tokenize(s: string): string[] {
  const out: string[] = []
  let cur = ''
  let quote: '"' | "'" | null = null
  for (const ch of s) {
    if (quote) {
      if (ch === quote) quote = null
      else cur += ch
    } else if (ch === '"' || ch === "'") {
      quote = ch
    } else if (/\s/.test(ch)) {
      if (cur) {
        out.push(cur)
        cur = ''
      }
    } else {
      cur += ch
    }
  }
  if (quote) throw new SandboxCommandError('unbalanced quote in command')
  if (cur) out.push(cur)
  return out
}
