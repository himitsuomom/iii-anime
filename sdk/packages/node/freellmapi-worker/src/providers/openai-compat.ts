import type {
  ChatCompletion,
  ChatCompletionChunk,
  ChatMessage,
  CompletionOptions,
  ProviderModel,
} from '../types.js'
import { ProviderHttpError } from '../types.js'
import { BaseProvider, makeId, parseRetryAfterMs } from './base.js'

interface OpenAICompatConfig {
  platform: string
  name: string
  baseUrl: string
  models: ProviderModel[]
  keyless?: boolean
  extraHeaders?: Record<string, string>
  timeoutMs?: number
  singleToolCallOnly?: boolean
}

export class OpenAICompatProvider extends BaseProvider {
  readonly platform: string
  readonly name: string
  readonly models: ProviderModel[]
  readonly keyless: boolean
  private readonly baseUrl: string
  private readonly extraHeaders: Record<string, string>
  private readonly timeoutMs: number
  private readonly singleToolCallOnly: boolean

  constructor(config: OpenAICompatConfig) {
    super()
    this.platform = config.platform
    this.name = config.name
    this.baseUrl = config.baseUrl.replace(/\/$/, '')
    this.models = config.models
    this.keyless = config.keyless ?? false
    this.extraHeaders = config.extraHeaders ?? {}
    this.timeoutMs = config.timeoutMs ?? 15_000
    this.singleToolCallOnly = config.singleToolCallOnly ?? false
  }

  private authHeader(apiKey: string): Record<string, string> {
    if (this.keyless) return {}
    return { Authorization: `Bearer ${apiKey}` }
  }

  async chatCompletion(
    apiKey: string,
    messages: ChatMessage[],
    options: CompletionOptions,
  ): Promise<ChatCompletion> {
    const body: Record<string, unknown> = {
      model: options.model,
      messages,
      temperature: options.temperature,
      max_tokens: options.max_tokens,
      top_p: options.top_p,
    }
    if (options.tools?.length) {
      body.tools = options.tools
      body.tool_choice = options.tool_choice ?? 'auto'
      if (this.singleToolCallOnly) {
        body.parallel_tool_calls = false
      } else {
        body.parallel_tool_calls = options.parallel_tool_calls
      }
    }

    const resp = await this.fetchWithTimeout(
      `${this.baseUrl}/chat/completions`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...this.authHeader(apiKey),
          ...this.extraHeaders,
        },
        body: JSON.stringify(body),
      },
      this.timeoutMs,
    )

    if (!resp.ok) {
      const retryAfterMs = parseRetryAfterMs(resp.headers.get('Retry-After'))
      const text = await resp.text().catch(() => '')
      throw new ProviderHttpError(
        `${this.name} returned ${resp.status}: ${text.slice(0, 200)}`,
        resp.status,
        retryAfterMs,
      )
    }

    const data = (await resp.json()) as ChatCompletion
    return data
  }

  async *streamChatCompletion(
    apiKey: string,
    messages: ChatMessage[],
    options: CompletionOptions,
  ): AsyncGenerator<ChatCompletionChunk> {
    const body: Record<string, unknown> = {
      model: options.model,
      messages,
      temperature: options.temperature,
      max_tokens: options.max_tokens,
      top_p: options.top_p,
      stream: true,
    }
    if (options.tools?.length) {
      body.tools = options.tools
      body.tool_choice = options.tool_choice ?? 'auto'
      if (this.singleToolCallOnly) {
        body.parallel_tool_calls = false
      } else {
        body.parallel_tool_calls = options.parallel_tool_calls
      }
    }

    const resp = await this.fetchWithTimeout(
      `${this.baseUrl}/chat/completions`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...this.authHeader(apiKey),
          ...this.extraHeaders,
        },
        body: JSON.stringify(body),
      },
      this.timeoutMs,
    )

    if (!resp.ok) {
      const retryAfterMs = parseRetryAfterMs(resp.headers.get('Retry-After'))
      const text = await resp.text().catch(() => '')
      throw new ProviderHttpError(
        `${this.name} returned ${resp.status}: ${text.slice(0, 200)}`,
        resp.status,
        retryAfterMs,
      )
    }

    for await (const line of this.readSseStream(resp)) {
      try {
        const chunk = JSON.parse(line) as ChatCompletionChunk
        yield chunk
      } catch {
        // skip malformed lines
      }
    }
  }

  async validateKey(apiKey: string): Promise<boolean> {
    try {
      const resp = await this.fetchWithTimeout(
        `${this.baseUrl}/models`,
        {
          method: 'GET',
          headers: {
            ...this.authHeader(apiKey),
            ...this.extraHeaders,
          },
        },
        8_000,
      )
      return resp.status !== 401 && resp.status !== 403
    } catch {
      return false
    }
  }
}

export function createOpenAICompatProvider(config: OpenAICompatConfig): OpenAICompatProvider {
  return new OpenAICompatProvider(config)
}

export const GROQ_MODELS: ProviderModel[] = [
  {
    id: 'llama-3.3-70b-versatile',
    displayName: 'Llama 3.3 70B Versatile (Groq)',
    contextWindow: 131072,
    supportsVision: false,
    supportsTools: true,
  },
  {
    id: 'llama-3.1-8b-instant',
    displayName: 'Llama 3.1 8B Instant (Groq)',
    contextWindow: 131072,
    supportsVision: false,
    supportsTools: true,
  },
  {
    id: 'mixtral-8x7b-32768',
    displayName: 'Mixtral 8x7B (Groq)',
    contextWindow: 32768,
    supportsVision: false,
    supportsTools: true,
  },
  {
    id: 'gemma2-9b-it',
    displayName: 'Gemma 2 9B (Groq)',
    contextWindow: 8192,
    supportsVision: false,
    supportsTools: true,
  },
]

export const CEREBRAS_MODELS: ProviderModel[] = [
  {
    id: 'llama3.1-70b',
    displayName: 'Llama 3.1 70B (Cerebras)',
    contextWindow: 131072,
    supportsVision: false,
    supportsTools: true,
  },
  {
    id: 'llama3.1-8b',
    displayName: 'Llama 3.1 8B (Cerebras)',
    contextWindow: 131072,
    supportsVision: false,
    supportsTools: true,
  },
  {
    id: 'qwen-3-32b',
    displayName: 'Qwen 3 32B (Cerebras)',
    contextWindow: 131072,
    supportsVision: false,
    supportsTools: true,
  },
]

export const MISTRAL_MODELS: ProviderModel[] = [
  {
    id: 'mistral-small-latest',
    displayName: 'Mistral Small (Mistral)',
    contextWindow: 32768,
    supportsVision: false,
    supportsTools: true,
  },
  {
    id: 'open-mistral-nemo',
    displayName: 'Mistral Nemo (Mistral)',
    contextWindow: 128000,
    supportsVision: false,
    supportsTools: true,
  },
]

export const makeId_export = makeId
