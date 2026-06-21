// OllamaBrain — run the factory "brain" on a local Ollama model instead of
// Claude. Fully local, no API key, no per-token cost. Good for the cheaper
// stages (intake/design/wiki); small CPU models are weaker at agentic build.
// HTTP is injected (FetchLike) so the logic is testable without a server.
import type { Brain, JsonRequest, TextRequest } from './brain.js'

export interface FetchLike {
  (
    input: string,
    init?: { method?: string; headers?: Record<string, string>; body?: string; signal?: AbortSignal },
  ): Promise<{ ok: boolean; status: number; text(): Promise<string> }>
}

export interface OllamaBrainOptions {
  host?: string
  model?: string
  fetchFn?: FetchLike
  timeoutMs?: number
}

export class OllamaBrain implements Brain {
  readonly id = 'ollama'
  private host: string
  private model: string
  private fetchFn: FetchLike
  private timeoutMs: number

  constructor(opts: OllamaBrainOptions = {}) {
    this.host = (opts.host ?? process.env.STUDIO_OLLAMA_HOST ?? 'http://127.0.0.1:11434').replace(/\/$/, '')
    this.model = opts.model ?? process.env.STUDIO_OLLAMA_MODEL ?? 'llama3.2'
    this.fetchFn = opts.fetchFn ?? ((input, init) => fetch(input, init as RequestInit))
    this.timeoutMs = opts.timeoutMs ?? 5 * 60_000
  }

  async json<T>(req: JsonRequest<T>): Promise<T> {
    const content = await this.chat(req.system, req.user, true)
    const parsed = parseJson(stripFences(content))
    if (parsed === null) throw new Error(`ollama output was not JSON: ${content.slice(0, 300)}`)
    return req.validate(parsed)
  }

  async text(req: TextRequest): Promise<string> {
    return this.chat(req.system, req.user, false)
  }

  private async chat(system: string, user: string, jsonMode: boolean): Promise<string> {
    const body = JSON.stringify({
      model: this.model,
      stream: false,
      ...(jsonMode ? { format: 'json' } : {}),
      messages: [
        { role: 'system', content: system },
        { role: 'user', content: user },
      ],
    })
    const ctrl = new AbortController()
    const timer = setTimeout(() => ctrl.abort(), this.timeoutMs)
    try {
      const res = await this.fetchFn(`${this.host}/api/chat`, {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body,
        signal: ctrl.signal,
      })
      const raw = await res.text()
      if (!res.ok) throw new Error(`ollama ${res.status}: ${raw.slice(0, 200)}`)
      const data = parseJson(raw)
      const content = data?.message?.content
      if (typeof content !== 'string') throw new Error(`ollama: no message content (${raw.slice(0, 200)})`)
      return content
    } finally {
      clearTimeout(timer)
    }
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
