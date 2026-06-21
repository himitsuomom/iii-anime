// The pluggable "brain" used for structured + free-text generation. Backends:
// ClaudeCliBrain (drives `claude -p`, no API key) here in studio-core; a factory
// supplies the validators that narrow JSON to its own domain types.
export interface JsonRequest<T> {
  system: string
  user: string
  /** Validate + narrow the parsed JSON; throw on a bad shape. */
  validate: (parsed: unknown) => T
  maxTurns?: number
}

export interface TextRequest {
  system: string
  user: string
  maxTurns?: number
}

export interface Brain {
  readonly id: string
  json<T>(req: JsonRequest<T>): Promise<T>
  /** Free-text generation (used by the wiki feature). */
  text(req: TextRequest): Promise<string>
}
