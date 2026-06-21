// Pluggable "brain" for studio::build. The build worker delegates "implement
// the app in this workdir and make the tests pass" to a backend. Two backends:
//   - ClaudeCodeBackend: drive the local Claude Code CLI (`claude -p`). Reuses
//     Claude Code's own sandbox/tools/loop and its existing login auth — runs
//     "from this Claude Code" with no separate ANTHROPIC_API_KEY wiring.
//   - ApiBackend (future): Anthropic Messages API + our own tool-use loop +
//     our sandbox::exec/edit. Needs ANTHROPIC_API_KEY, metered per token.
// See app-studio/BUILD-BACKENDS.md.

export interface BuildRequest {
  project_id: string
  /** Absolute path to the project's workspace; the backend works only here. */
  workdir: string
  /** Build instructions appended to the agent's system prompt. */
  systemPrompt: string
  /** The task message (spec + plan + "make the tests pass"). */
  userPrompt: string
  /** Hard cap on agent turns. */
  maxTurns?: number
}

export interface BuildOutcome {
  /** The backend process completed successfully (not a guarantee tests pass — QA decides that). */
  ok: boolean
  /** Final summary text from the agent. */
  summary: string
  num_turns?: number
  cost_usd?: number
  session_id?: string
  error?: string
  /** Backend-specific raw payload for tracing. */
  raw?: unknown
}

export interface BuildBackend {
  readonly id: string
  run(req: BuildRequest): Promise<BuildOutcome>
}
