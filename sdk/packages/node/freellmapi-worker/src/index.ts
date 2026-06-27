import { type ApiRequest, type ApiResponse } from 'iii-sdk'
import { z } from 'zod'
import { iii } from './iii.js'
import { getAllModels, getProvider } from './providers/index.js'
import type { Platform } from './providers/index.js'
import { routeWithRetry } from './router.js'
import type { ChatCompletionRequest, ChatMessage } from './types.js'
import { makeId } from './providers/base.js'

// ── helpers ──────────────────────────────────────────────────────────────────

function useApi<TBody = unknown>(
  config: { api_path: string; http_method: string; description?: string },
  handler: (req: ApiRequest<TBody>) => Promise<ApiResponse>,
): void {
  const function_id = `api::${config.http_method.toLowerCase()}::${config.api_path}`
  iii.registerFunction(function_id, (req: unknown) => handler(req as ApiRequest<TBody>))
  iii.registerTrigger({
    type: 'http',
    function_id,
    config: {
      api_path: config.api_path,
      http_method: config.http_method,
      description: config.description,
    },
  })
}

function json(body: Record<string, unknown> | null | object, status = 200): ApiResponse {
  return { status_code: status, body: body as Record<string, unknown>, headers: { 'Content-Type': 'application/json' } }
}

function errorJson(message: string, status = 500): ApiResponse {
  return json({ error: { message, type: 'api_error' } }, status)
}

// ── schema ───────────────────────────────────────────────────────────────────

const ChatMessageSchema: z.ZodType<ChatMessage> = z.lazy(() =>
  z.object({
    role: z.enum(['system', 'user', 'assistant', 'tool', 'developer']),
    content: z.union([z.string(), z.array(z.record(z.string(), z.unknown())), z.null()]).optional().default(''),
    name: z.string().optional(),
    tool_calls: z
      .array(
        z.object({
          id: z.string(),
          type: z.literal('function'),
          function: z.object({ name: z.string(), arguments: z.string() }),
        }),
      )
      .optional(),
    tool_call_id: z.string().optional(),
  }) as unknown as z.ZodType<ChatMessage>,
)

const ChatRequestSchema = z.object({
  model: z.string().optional(),
  messages: z.array(ChatMessageSchema),
  temperature: z.number().optional(),
  max_tokens: z.number().int().positive().optional(),
  top_p: z.number().optional(),
  stream: z.boolean().optional().default(false),
  tools: z.array(z.record(z.string(), z.unknown())).optional(),
  tool_choice: z.union([z.string(), z.record(z.string(), z.unknown())]).optional(),
  parallel_tool_calls: z.boolean().optional(),
})

// ── GET /freellm/models ──────────────────────────────────────────────────────

useApi(
  {
    api_path: 'freellm/models',
    http_method: 'GET',
    description: 'List all available free-tier LLM models aggregated by freellmapi-worker',
  },
  async () => {
    const models = getAllModels().map((m) => ({
      id: `${m.platform}/${m.id}`,
      object: 'model',
      created: Math.floor(Date.now() / 1000),
      owned_by: m.platform,
      description: m.displayName,
      context_window: m.contextWindow,
      supports_vision: m.supportsVision,
      supports_tools: m.supportsTools,
    }))
    return json({ object: 'list', data: models })
  },
)

// ── POST /freellm/v1/chat/completions ────────────────────────────────────────

useApi<ChatCompletionRequest>(
  {
    api_path: 'freellm/v1/chat/completions',
    http_method: 'POST',
    description:
      'OpenAI-compatible chat completions endpoint. Routes requests to the best available free-tier provider (Google Gemini, Groq, Cerebras, Mistral, etc.).',
  },
  async (req) => {
    let parsed: z.infer<typeof ChatRequestSchema>
    try {
      parsed = ChatRequestSchema.parse(req.body)
    } catch (err) {
      return errorJson(`Invalid request: ${String(err)}`, 400)
    }

    // Determine whether vision or tool-calling is required
    const requireVision =
      parsed.messages.some(
        (m) =>
          Array.isArray(m.content) && m.content.some((p) => (p as { type?: string }).type === 'image_url'),
      )
    const requireTools = !!(parsed.tools?.length)

    // Parse optional model preference: "platform/model-id" or just "model-id"
    let preferredPlatform: Platform | undefined
    let preferredModelId: string | undefined
    if (parsed.model) {
      const slash = parsed.model.indexOf('/')
      if (slash !== -1) {
        preferredPlatform = parsed.model.slice(0, slash) as Platform
        preferredModelId = parsed.model.slice(slash + 1)
      } else {
        preferredModelId = parsed.model
      }
    }

    const messages = parsed.messages as ChatMessage[]
    const options = {
      temperature: parsed.temperature,
      max_tokens: parsed.max_tokens,
      top_p: parsed.top_p,
      tools: parsed.tools as ChatCompletionRequest['tools'],
      tool_choice: parsed.tool_choice as ChatCompletionRequest['tool_choice'],
      parallel_tool_calls: parsed.parallel_tool_calls,
    }

    if (parsed.stream) {
      // Streaming: collect all chunks and return a joined response
      // (iii HTTP triggers do not yet support chunked SSE responses natively)
      try {
        const chunks: string[] = ['data: ']
        let finalModel = ''
        let finalId = makeId()

        await routeWithRetry({ requireVision, requireTools, preferredPlatform, preferredModelId }, async (route) => {
          finalModel = `${route.platform}/${route.modelId}`
          finalId = makeId()
          const gen = route.provider.streamChatCompletion(route.apiKey, messages, {
            model: route.modelId,
            ...options,
          })
          for await (const chunk of gen) {
            chunk.model = finalModel
            chunk.id = finalId
            chunks.push(`data: ${JSON.stringify(chunk)}\n\n`)
          }
        })

        chunks.push('data: [DONE]\n\n')
        return {
          status_code: 200,
          body: chunks.join(''),
          headers: {
            'Content-Type': 'text/event-stream',
            'Cache-Control': 'no-cache',
            Connection: 'keep-alive',
          },
        }
      } catch (err) {
        return errorJson(String(err), 503)
      }
    }

    // Non-streaming
    try {
      let completion = null
      await routeWithRetry({ requireVision, requireTools, preferredPlatform, preferredModelId }, async (route) => {
        const result = await route.provider.chatCompletion(route.apiKey, messages, {
          model: route.modelId,
          ...options,
        })
        result.model = `${route.platform}/${route.modelId}`
        completion = result
      })
      return json(completion)
    } catch (err) {
      const msg = String(err)
      if (msg.includes('no_route') || msg.includes('exhausted') || msg.includes('API key')) {
        return errorJson('No available provider. Set one or more API key env vars (GROQ_API_KEY, GOOGLE_API_KEY, CEREBRAS_API_KEY, MISTRAL_API_KEY).', 503)
      }
      return errorJson(msg, 502)
    }
  },
)

// ── POST /freellm/v1/chat/completions/:platform ──────────────────────────────

useApi<ChatCompletionRequest>(
  {
    api_path: 'freellm/v1/providers/:platform/chat/completions',
    http_method: 'POST',
    description:
      'Route a chat completion directly to a specific provider platform (e.g. groq, google, cerebras, mistral)',
  },
  async (req) => {
    const platform = req.path_params?.platform as Platform | undefined
    if (!platform) return errorJson('Missing platform path param', 400)

    const provider = getProvider(platform)
    if (!provider) return errorJson(`Unknown platform: ${platform}`, 404)

    let parsed: z.infer<typeof ChatRequestSchema>
    try {
      parsed = ChatRequestSchema.parse(req.body)
    } catch (err) {
      return errorJson(`Invalid request: ${String(err)}`, 400)
    }

    const modelId = parsed.model ?? provider.models[0]?.id
    if (!modelId) return errorJson(`No model available for platform: ${platform}`, 503)

    const { getAvailableKey } = await import('./keys.js')
    const apiKey = getAvailableKey(platform)
    if (!apiKey && !provider.keyless) {
      return errorJson(`No API key configured for ${platform}. Set ${platform.toUpperCase()}_API_KEY.`, 503)
    }

    const messages = parsed.messages as ChatMessage[]
    const options = {
      model: modelId,
      temperature: parsed.temperature,
      max_tokens: parsed.max_tokens,
      top_p: parsed.top_p,
      tools: parsed.tools as ChatCompletionRequest['tools'],
      tool_choice: parsed.tool_choice as ChatCompletionRequest['tool_choice'],
      parallel_tool_calls: parsed.parallel_tool_calls,
    }

    try {
      const completion = await provider.chatCompletion(apiKey ?? '__keyless__', messages, options)
      completion.model = `${platform}/${modelId}`
      return json(completion)
    } catch (err) {
      return errorJson(String(err), 502)
    }
  },
)

// ── GET /freellm/health ───────────────────────────────────────────────────────

useApi(
  {
    api_path: 'freellm/health',
    http_method: 'GET',
    description: 'Health check for the freellmapi worker',
  },
  async () => {
    const models = getAllModels()
    return json({
      status: 'ok',
      worker: 'freellmapi-worker',
      model_count: models.length,
      configured_keys: {
        groq: !!process.env.GROQ_API_KEY,
        google: !!process.env.GOOGLE_API_KEY,
        cerebras: !!process.env.CEREBRAS_API_KEY,
        mistral: !!process.env.MISTRAL_API_KEY,
        openrouter: !!process.env.OPENROUTER_API_KEY,
        pollinations: true,
      },
    })
  },
)

console.log('[freellmapi-worker] registered endpoints:')
console.log('  GET  /freellm/models')
console.log('  GET  /freellm/health')
console.log('  POST /freellm/v1/chat/completions')
console.log('  POST /freellm/v1/providers/:platform/chat/completions')
