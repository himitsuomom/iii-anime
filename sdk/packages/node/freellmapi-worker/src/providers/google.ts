import type {
  ChatCompletion,
  ChatCompletionChunk,
  ChatMessage,
  CompletionOptions,
  ProviderModel,
} from '../types.js'
import { ProviderHttpError } from '../types.js'
import { BaseProvider, makeId, parseRetryAfterMs } from './base.js'

const GEMINI_BASE = 'https://generativelanguage.googleapis.com/v1beta'

export const GOOGLE_MODELS: ProviderModel[] = [
  {
    id: 'gemini-2.0-flash',
    displayName: 'Gemini 2.0 Flash (Google)',
    contextWindow: 1048576,
    supportsVision: true,
    supportsTools: true,
  },
  {
    id: 'gemini-1.5-flash',
    displayName: 'Gemini 1.5 Flash (Google)',
    contextWindow: 1048576,
    supportsVision: true,
    supportsTools: true,
  },
  {
    id: 'gemini-1.5-flash-8b',
    displayName: 'Gemini 1.5 Flash 8B (Google)',
    contextWindow: 1048576,
    supportsVision: true,
    supportsTools: true,
  },
]

type GeminiRole = 'user' | 'model'

interface GeminiPart {
  text?: string
  inlineData?: { mimeType: string; data: string }
  functionCall?: { name: string; args: Record<string, unknown> }
  functionResponse?: { name: string; response: Record<string, unknown> }
}

interface GeminiContent {
  role: GeminiRole
  parts: GeminiPart[]
}

interface GeminiFunctionDeclaration {
  name: string
  description?: string
  parameters?: Record<string, unknown>
}

function toGeminiMessages(messages: ChatMessage[]): {
  systemInstruction?: { parts: GeminiPart[] }
  contents: GeminiContent[]
} {
  let systemInstruction: { parts: GeminiPart[] } | undefined
  const contents: GeminiContent[] = []

  for (const msg of messages) {
    if (msg.role === 'system' || msg.role === 'developer') {
      const text = typeof msg.content === 'string' ? msg.content : ''
      systemInstruction = { parts: [{ text }] }
      continue
    }

    if (msg.role === 'tool') {
      const lastContent = contents[contents.length - 1]
      if (lastContent?.role === 'user') {
        lastContent.parts.push({
          functionResponse: {
            name: msg.name ?? 'tool',
            response: { content: msg.content ?? '' },
          },
        })
      } else {
        contents.push({
          role: 'user',
          parts: [
            {
              functionResponse: {
                name: msg.name ?? 'tool',
                response: { content: msg.content ?? '' },
              },
            },
          ],
        })
      }
      continue
    }

    const role: GeminiRole = msg.role === 'assistant' ? 'model' : 'user'
    const parts: GeminiPart[] = []

    if (msg.tool_calls?.length) {
      for (const tc of msg.tool_calls) {
        try {
          parts.push({
            functionCall: {
              name: tc.function.name,
              args: JSON.parse(tc.function.arguments || '{}'),
            },
          })
        } catch {
          parts.push({ functionCall: { name: tc.function.name, args: {} } })
        }
      }
    } else if (typeof msg.content === 'string') {
      parts.push({ text: msg.content })
    } else if (Array.isArray(msg.content)) {
      for (const part of msg.content) {
        if (part.type === 'text' && part.text) {
          parts.push({ text: part.text })
        }
      }
    }

    if (parts.length === 0) parts.push({ text: '' })
    contents.push({ role, parts })
  }

  return { systemInstruction, contents }
}

function fromGeminiResponse(
  data: Record<string, unknown>,
  modelId: string,
  id: string,
): ChatCompletion {
  const candidates = (data.candidates as Array<Record<string, unknown>>) ?? []
  const usageMeta = data.usageMetadata as Record<string, number> | undefined

  const choices = candidates.map((c, i) => {
    const content = c.content as { parts?: GeminiPart[] } | undefined
    const parts = content?.parts ?? []
    const finishReason = (c.finishReason as string | undefined) ?? 'stop'

    const toolCalls = parts
      .filter((p) => p.functionCall)
      .map((p, idx) => ({
        id: `call_${id}_${idx}`,
        type: 'function' as const,
        function: {
          name: p.functionCall!.name,
          arguments: JSON.stringify(p.functionCall!.args ?? {}),
        },
      }))

    const textParts = parts.filter((p) => p.text).map((p) => p.text!)
    const text = textParts.join('')

    return {
      index: i,
      message: {
        role: 'assistant' as const,
        content: toolCalls.length ? null : text,
        tool_calls: toolCalls.length ? toolCalls : undefined,
      },
      finish_reason: (
        finishReason === 'STOP'
          ? 'stop'
          : finishReason === 'MAX_TOKENS'
            ? 'length'
            : finishReason === 'SAFETY'
              ? 'content_filter'
              : finishReason === 'RECITATION'
                ? 'content_filter'
                : finishReason.includes('TOOL') || finishReason === 'FUNCTION_CALL'
                  ? 'tool_calls'
                  : 'stop'
      ) as ChatCompletion['choices'][number]['finish_reason'],
    }
  })

  return {
    id,
    object: 'chat.completion',
    created: Math.floor(Date.now() / 1000),
    model: modelId,
    choices,
    usage: usageMeta
      ? {
          prompt_tokens: usageMeta.promptTokenCount ?? 0,
          completion_tokens: usageMeta.candidatesTokenCount ?? 0,
          total_tokens: usageMeta.totalTokenCount ?? 0,
        }
      : undefined,
  }
}

export class GoogleProvider extends BaseProvider {
  readonly platform = 'google'
  readonly name = 'Google Gemini'
  readonly models = GOOGLE_MODELS

  private buildBody(messages: ChatMessage[], options: CompletionOptions): Record<string, unknown> {
    const { systemInstruction, contents } = toGeminiMessages(messages)
    const body: Record<string, unknown> = { contents }
    if (systemInstruction) body.systemInstruction = systemInstruction

    const config: Record<string, unknown> = {}
    if (options.temperature !== undefined) config.temperature = options.temperature
    if (options.max_tokens !== undefined) config.maxOutputTokens = options.max_tokens
    if (options.top_p !== undefined) config.topP = options.top_p
    if (Object.keys(config).length) body.generationConfig = config

    if (options.tools?.length) {
      const functionDeclarations: GeminiFunctionDeclaration[] = options.tools
        .filter((t) => t.type === 'function')
        .map((t) => ({
          name: t.function.name,
          description: t.function.description,
          parameters: t.function.parameters,
        }))
      body.tools = [{ functionDeclarations }]
    }

    return body
  }

  async chatCompletion(
    apiKey: string,
    messages: ChatMessage[],
    options: CompletionOptions,
  ): Promise<ChatCompletion> {
    const modelId = options.model
    const url = `${GEMINI_BASE}/models/${modelId}:generateContent?key=${apiKey}`
    const body = this.buildBody(messages, options)

    const resp = await this.fetchWithTimeout(
      url,
      { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) },
      options.timeoutMs ?? 30_000,
    )

    if (!resp.ok) {
      const retryAfterMs = parseRetryAfterMs(resp.headers.get('Retry-After'))
      const text = await resp.text().catch(() => '')
      throw new ProviderHttpError(`Google returned ${resp.status}: ${text.slice(0, 200)}`, resp.status, retryAfterMs)
    }

    const data = (await resp.json()) as Record<string, unknown>
    const id = makeId('chatcmpl')
    return fromGeminiResponse(data, modelId, id)
  }

  async *streamChatCompletion(
    apiKey: string,
    messages: ChatMessage[],
    options: CompletionOptions,
  ): AsyncGenerator<ChatCompletionChunk> {
    const modelId = options.model
    const url = `${GEMINI_BASE}/models/${modelId}:streamGenerateContent?alt=sse&key=${apiKey}`
    const body = this.buildBody(messages, options)

    const resp = await this.fetchWithTimeout(
      url,
      { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) },
      options.timeoutMs ?? 30_000,
    )

    if (!resp.ok) {
      const retryAfterMs = parseRetryAfterMs(resp.headers.get('Retry-After'))
      const text = await resp.text().catch(() => '')
      throw new ProviderHttpError(`Google returned ${resp.status}: ${text.slice(0, 200)}`, resp.status, retryAfterMs)
    }

    const id = makeId('chatcmpl')

    for await (const line of this.readSseStream(resp)) {
      try {
        const data = JSON.parse(line) as Record<string, unknown>
        const completion = fromGeminiResponse(data, modelId, id)
        yield {
          id,
          object: 'chat.completion.chunk',
          created: completion.created,
          model: modelId,
          choices: completion.choices.map((c) => ({
            index: c.index,
            delta: c.message,
            finish_reason: c.finish_reason,
          })),
        }
      } catch {
        // skip malformed lines
      }
    }
  }

  async validateKey(apiKey: string): Promise<boolean> {
    try {
      const resp = await this.fetchWithTimeout(
        `${GEMINI_BASE}/models?key=${apiKey}`,
        { method: 'GET' },
        8_000,
      )
      return resp.status !== 400 && resp.status !== 403
    } catch {
      return false
    }
  }
}
