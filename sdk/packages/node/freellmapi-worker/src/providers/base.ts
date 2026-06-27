import type {
  ChatCompletion,
  ChatCompletionChunk,
  ChatMessage,
  CompletionOptions,
  Provider,
  ProviderModel,
} from '../types.js'
import { ProviderHttpError } from '../types.js'

export function parseRetryAfterMs(header: string | null): number | undefined {
  if (!header) return undefined
  const seconds = Number(header)
  if (!Number.isNaN(seconds)) return seconds * 1000
  const date = Date.parse(header)
  if (!Number.isNaN(date)) return Math.max(0, date - Date.now())
  return undefined
}

export function makeId(prefix = 'chatcmpl'): string {
  return `${prefix}-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 9)}`
}

export abstract class BaseProvider implements Provider {
  abstract readonly platform: string
  abstract readonly name: string
  abstract readonly models: ProviderModel[]
  readonly keyless: boolean = false

  abstract chatCompletion(
    apiKey: string,
    messages: ChatMessage[],
    options: CompletionOptions,
  ): Promise<ChatCompletion>

  abstract streamChatCompletion(
    apiKey: string,
    messages: ChatMessage[],
    options: CompletionOptions,
  ): AsyncGenerator<ChatCompletionChunk>

  abstract validateKey(apiKey: string): Promise<boolean>

  protected async fetchWithTimeout(
    url: string,
    init: RequestInit,
    timeoutMs = 15_000,
  ): Promise<Response> {
    const controller = new AbortController()
    const timer = setTimeout(() => controller.abort(), timeoutMs)
    try {
      return await fetch(url, { ...init, signal: controller.signal })
    } finally {
      clearTimeout(timer)
    }
  }

  protected async *readSseStream(
    response: Response,
    inactivityTimeoutMs = 30_000,
  ): AsyncGenerator<string> {
    if (!response.body) throw new ProviderHttpError('No response body')

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    let lastChunkAt = Date.now()

    while (true) {
      const deadline = inactivityTimeoutMs - (Date.now() - lastChunkAt)
      if (deadline <= 0) throw new ProviderHttpError('SSE inactivity timeout')

      const readPromise = reader.read()
      const timeoutPromise = new Promise<never>((_, reject) =>
        setTimeout(() => reject(new ProviderHttpError('SSE inactivity timeout')), deadline),
      )

      const { done, value } = await Promise.race([readPromise, timeoutPromise])
      if (done) break

      lastChunkAt = Date.now()
      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() ?? ''

      for (const line of lines) {
        const trimmed = line.trim()
        if (!trimmed || trimmed === ':') continue
        if (trimmed.startsWith('data:')) {
          const data = trimmed.slice(5).trim()
          if (data === '[DONE]') return
          yield data
        }
      }
    }

    if (buffer.trim().startsWith('data:')) {
      const data = buffer.trim().slice(5).trim()
      if (data && data !== '[DONE]') yield data
    }
  }
}
