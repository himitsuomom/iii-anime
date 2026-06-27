import type { Provider, ProviderModel } from '../types.js'
import { GoogleProvider } from './google.js'
import {
  CEREBRAS_MODELS,
  GROQ_MODELS,
  MISTRAL_MODELS,
  OpenAICompatProvider,
} from './openai-compat.js'

export type Platform = 'groq' | 'google' | 'cerebras' | 'mistral' | 'openrouter' | 'cohere' | 'pollinations' | 'custom'

const registry = new Map<Platform, Provider>()

function register(platform: Platform, provider: Provider): void {
  registry.set(platform, provider)
}

register(
  'google',
  new GoogleProvider(),
)

register(
  'groq',
  new OpenAICompatProvider({
    platform: 'groq',
    name: 'Groq',
    baseUrl: 'https://api.groq.com/openai/v1',
    models: GROQ_MODELS,
  }),
)

register(
  'cerebras',
  new OpenAICompatProvider({
    platform: 'cerebras',
    name: 'Cerebras',
    baseUrl: 'https://api.cerebras.ai/v1',
    models: CEREBRAS_MODELS,
  }),
)

register(
  'mistral',
  new OpenAICompatProvider({
    platform: 'mistral',
    name: 'Mistral',
    baseUrl: 'https://api.mistral.ai/v1',
    models: MISTRAL_MODELS,
  }),
)

register(
  'openrouter',
  new OpenAICompatProvider({
    platform: 'openrouter',
    name: 'OpenRouter',
    baseUrl: 'https://openrouter.ai/api/v1',
    models: [],
    extraHeaders: {
      'HTTP-Referer': 'https://iii.dev',
      'X-Title': 'iii freellmapi-worker',
    },
  }),
)

register(
  'pollinations',
  new OpenAICompatProvider({
    platform: 'pollinations',
    name: 'Pollinations',
    baseUrl: 'https://text.pollinations.ai/openai',
    models: [
      {
        id: 'openai',
        displayName: 'GPT-4o via Pollinations (free)',
        contextWindow: 128000,
        supportsVision: true,
        supportsTools: false,
        description: 'Free tier via Pollinations proxy',
      },
      {
        id: 'mistral',
        displayName: 'Mistral via Pollinations (free)',
        contextWindow: 32768,
        supportsVision: false,
        supportsTools: false,
      },
    ],
    keyless: true,
  }),
)

export function getProvider(platform: Platform): Provider | undefined {
  return registry.get(platform)
}

export function getAllProviders(): Array<{ platform: Platform; provider: Provider }> {
  return Array.from(registry.entries()).map(([platform, provider]) => ({ platform, provider }))
}

export function getAllModels(): Array<ProviderModel & { platform: Platform }> {
  const models: Array<ProviderModel & { platform: Platform }> = []
  for (const [platform, provider] of registry.entries()) {
    for (const model of provider.models) {
      models.push({ ...model, platform })
    }
  }
  return models
}

export function resolveProvider(
  platform: Platform,
  customBaseUrl?: string,
): Provider | undefined {
  if (platform === 'custom' && customBaseUrl) {
    return new OpenAICompatProvider({
      platform: 'custom',
      name: 'Custom',
      baseUrl: customBaseUrl,
      models: [],
      timeoutMs: 120_000,
    })
  }
  return registry.get(platform)
}
