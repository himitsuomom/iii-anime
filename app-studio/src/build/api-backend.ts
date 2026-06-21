// ApiBackend — the second build "brain": the Anthropic Messages API plus our
// own tool-use loop bridged to sandbox::exec / sandbox::edit. Unlike the Claude
// Code backend, the loop and the execution boundary are ours (allowlist +
// workdir confinement). Needs ANTHROPIC_API_KEY (metered). The Anthropic client
// is injected structurally so the loop is testable without the SDK or a key.
import type { BuildBackend, BuildOutcome, BuildRequest } from './backend.js'
import type { EditInput } from '../sandbox/edit.js'
import { editInWorkspace } from '../sandbox/edit.js'
import { execInWorkspace } from '../sandbox/exec.js'
import { ensureWorkspace } from '../sandbox/workspace.js'

export interface ToolUseBlock {
  type: 'tool_use'
  id: string
  name: string
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  input: any
}
export type ContentBlock = ToolUseBlock | { type: string; [k: string]: unknown }

export interface MessageResponse {
  stop_reason: string | null
  content: ContentBlock[]
}

/** Structural subset of the Anthropic SDK we depend on (so tests can fake it). */
export interface MessagesClient {
  create(params: Record<string, unknown>): Promise<MessageResponse>
}

export interface ApiBackendOptions {
  model?: string
  maxTokens?: number
}

const TOOLS = [
  { type: 'bash_20250124', name: 'bash' },
  { type: 'text_editor_20250728', name: 'str_replace_based_edit_tool' },
]

export class ApiBackend implements BuildBackend {
  readonly id = 'api'
  private model: string
  private maxTokens: number

  constructor(
    private client: MessagesClient,
    opts: ApiBackendOptions = {},
  ) {
    this.model = opts.model ?? 'claude-opus-4-8'
    this.maxTokens = opts.maxTokens ?? 16000
  }

  async run(req: BuildRequest): Promise<BuildOutcome> {
    await ensureWorkspace(req.project_id)
    const maxTurns = req.maxTurns ?? 60
    const messages: Array<{ role: 'user' | 'assistant'; content: unknown }> = [
      { role: 'user', content: req.userPrompt },
    ]

    for (let turn = 0; turn < maxTurns; turn++) {
      const res = await this.client.create({
        model: this.model,
        max_tokens: this.maxTokens,
        thinking: { type: 'adaptive' },
        output_config: { effort: 'xhigh' },
        system: req.systemPrompt,
        tools: TOOLS,
        messages,
      })

      if (res.stop_reason === 'refusal') {
        return { ok: false, summary: '', error: 'refusal', num_turns: turn + 1 }
      }

      messages.push({ role: 'assistant', content: res.content })
      const toolUses = res.content.filter((b): b is ToolUseBlock => b.type === 'tool_use')
      if (toolUses.length === 0) {
        return { ok: true, summary: collectText(res.content), num_turns: turn + 1 }
      }

      const results = []
      for (const t of toolUses) {
        const { text, isError } = await this.bridge(req.project_id, t)
        results.push({ type: 'tool_result', tool_use_id: t.id, content: text, is_error: isError })
      }
      messages.push({ role: 'user', content: results })
    }

    return { ok: false, summary: '', error: `exceeded ${maxTurns} turns`, num_turns: maxTurns }
  }

  private async bridge(
    projectId: string,
    tool: ToolUseBlock,
  ): Promise<{ text: string; isError: boolean }> {
    try {
      if (tool.name === 'bash') {
        if (tool.input?.restart) return { text: 'shell restarted', isError: false }
        const r = await execInWorkspace({
          project_id: projectId,
          cmd: String(tool.input?.command ?? ''),
        })
        const text = `exit ${r.exit_code}${r.timed_out ? ' (timeout)' : ''}\n--- stdout ---\n${cap(r.stdout)}\n--- stderr ---\n${cap(r.stderr)}`
        return { text, isError: r.exit_code !== 0 || r.timed_out }
      }
      // text editor — field names match EditInput one-to-one
      const input = tool.input as Partial<EditInput>
      const r = await editInWorkspace({
        project_id: projectId,
        command: (input.command ?? 'view') as EditInput['command'],
        path: String(input.path ?? ''),
        file_text: input.file_text,
        old_str: input.old_str,
        new_str: input.new_str,
        insert_line: input.insert_line,
        insert_text: input.insert_text,
        view_range: input.view_range,
      })
      return { text: r.error ?? r.content ?? r.diff ?? 'ok', isError: !r.ok }
    } catch (err) {
      // Sandbox rejections (disallowed command, escape) must not crash the
      // build — return them so the model can correct course.
      return { text: err instanceof Error ? err.message : String(err), isError: true }
    }
  }
}

function collectText(content: ContentBlock[]): string {
  return content
    .filter((b): b is { type: 'text'; text: string } => b.type === 'text')
    .map((b) => b.text)
    .join('')
}

function cap(s: string, n = 4000): string {
  return s.length > n ? `${s.slice(0, n)}…` : s
}
