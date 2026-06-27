export interface ChatMessage {
  role: 'system' | 'user' | 'assistant' | 'tool' | 'developer'
  content: string | ContentPart[] | null
  name?: string
  tool_calls?: ToolCall[]
  tool_call_id?: string
}

export interface ContentPart {
  type: 'text' | 'image_url'
  text?: string
  image_url?: { url: string; detail?: string }
}

export interface ToolCall {
  id: string
  type: 'function'
  function: { name: string; arguments: string }
}

export interface Tool {
  type: 'function'
  function: {
    name: string
    description?: string
    parameters?: Record<string, unknown>
    strict?: boolean
  }
}

export interface ChatCompletionRequest {
  model?: string
  messages: ChatMessage[]
  temperature?: number
  max_tokens?: number
  top_p?: number
  stream?: boolean
  tools?: Tool[]
  tool_choice?: string | { type: string; function?: { name: string } }
  parallel_tool_calls?: boolean
  stop?: string | string[]
  user?: string
  [key: string]: unknown
}

export interface ChatCompletionChoice {
  index: number
  message: ChatMessage
  finish_reason: 'stop' | 'length' | 'tool_calls' | 'content_filter' | null
  delta?: Partial<ChatMessage>
}

export interface ChatCompletionUsage {
  prompt_tokens: number
  completion_tokens: number
  total_tokens: number
}

export interface ChatCompletion {
  id: string
  object: 'chat.completion'
  created: number
  model: string
  choices: ChatCompletionChoice[]
  usage?: ChatCompletionUsage
}

export interface ChatCompletionChunk {
  id: string
  object: 'chat.completion.chunk'
  created: number
  model: string
  choices: Array<{
    index: number
    delta: Partial<ChatMessage>
    finish_reason: string | null
  }>
}

export interface ModelInfo {
  id: string
  object: 'model'
  created: number
  owned_by: string
  description?: string
}

export interface CompletionOptions {
  model: string
  temperature?: number
  max_tokens?: number
  top_p?: number
  tools?: Tool[]
  tool_choice?: ChatCompletionRequest['tool_choice']
  parallel_tool_calls?: boolean
  timeoutMs?: number
}

export interface ProviderModel {
  id: string
  displayName: string
  contextWindow: number
  supportsVision: boolean
  supportsTools: boolean
  description?: string
}

export interface Provider {
  readonly platform: string
  readonly name: string
  readonly models: ProviderModel[]
  readonly keyless: boolean
  chatCompletion(
    apiKey: string,
    messages: ChatMessage[],
    options: CompletionOptions,
  ): Promise<ChatCompletion>
  streamChatCompletion(
    apiKey: string,
    messages: ChatMessage[],
    options: CompletionOptions,
  ): AsyncGenerator<ChatCompletionChunk>
  validateKey(apiKey: string): Promise<boolean>
}

export class ProviderHttpError extends Error {
  constructor(
    message: string,
    public readonly status?: number,
    public readonly retryAfterMs?: number,
  ) {
    super(message)
    this.name = 'ProviderHttpError'
  }
}

export interface RouteResult {
  provider: Provider
  modelId: string
  apiKey: string
  displayName: string
}
