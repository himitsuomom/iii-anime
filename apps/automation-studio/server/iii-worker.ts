/**
 * Registers automation-studio's AI capabilities as iii worker functions so
 * other workers (e.g. apps/ec) can invoke them over the engine by id:
 *   - ai::describe-product  → shared generateDescription (opus / template)
 *   - ai::answer-inquiry    → shared answerInquiry (opus / FAQ)
 *
 * The iii SDK import is confined to this module; the shared lib functions
 * (lib/describe.ts, lib/inquiry.ts) stay engine-independent and unit-testable.
 * HTTP access already exists via the Hono routes, so these are registered as
 * trigger-invocable functions only (no HTTP triggers, avoiding response-shape
 * coupling).
 */
import { DESCRIBE_OUTPUT_SCHEMA, generateDescription } from './lib/describe.ts'
import { answerInquiry, type ChatMessage } from './lib/inquiry.ts'
import type { DescriptionInput } from './lib/offline.ts'

/** Minimal structural type of the engine instance we depend on (keeps this testable). */
export interface IIIEngine {
  registerFunction: (
    id: string,
    handler: (data: unknown) => Promise<unknown>,
    options?: Record<string, unknown>,
  ) => unknown
  shutdown?: () => void
}

const DESCRIBE_REQUEST_SCHEMA = {
  type: 'object',
  properties: {
    productName: { type: 'string' },
    features: { type: 'string' },
    keywords: { type: 'string' },
    tone: { type: 'string' },
  },
  required: ['productName'],
} as const

/** Accept both a raw trigger() payload and an HTTP ApiRequest envelope ({ body }). */
function unwrap(data: unknown): Record<string, unknown> {
  if (data && typeof data === 'object') {
    const obj = data as Record<string, unknown>
    if ('body' in obj && ('method' in obj || 'headers' in obj || 'path_params' in obj)) {
      const body = obj.body
      return body && typeof body === 'object' ? (body as Record<string, unknown>) : {}
    }
    return obj
  }
  return {}
}

/** Register the AI functions on an engine instance. Exported for unit testing. */
export function registerAiFunctions(iii: IIIEngine): void {
  iii.registerFunction(
    'ai::describe-product',
    async (data: unknown) => {
      const body = unwrap(data) as Partial<DescriptionInput>
      const { result, source } = await generateDescription(body)
      return { ...result, source }
    },
    {
      description: 'Generate an SEO product description (Claude opus, template fallback).',
      request_format: DESCRIBE_REQUEST_SCHEMA,
      response_format: DESCRIBE_OUTPUT_SCHEMA,
    },
  )

  iii.registerFunction(
    'ai::answer-inquiry',
    async (data: unknown) => {
      const body = unwrap(data)
      const messages = (body.messages ?? []) as ChatMessage[]
      return await answerInquiry(messages)
    },
    { description: 'Answer a customer inquiry (Claude opus, FAQ fallback).' },
  )
}

/**
 * Connect to the engine and register the AI functions. Returns the engine
 * instance (with shutdown) or null when III_URL is not configured.
 */
export async function startAiWorker(url: string | undefined): Promise<IIIEngine | null> {
  if (!url) return null
  const { registerWorker } = await import('iii-sdk')
  const iii = registerWorker(url) as unknown as IIIEngine
  registerAiFunctions(iii)
  return iii
}
