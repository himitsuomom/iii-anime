import type { Platform } from './providers/index.js'
import { getAllProviders } from './providers/index.js'
import { getAvailableKey, setCooldown } from './keys.js'
import type { Provider, ProviderModel, RouteResult } from './types.js'
import { ProviderHttpError } from './types.js'

export interface RouteOptions {
  requireVision?: boolean
  requireTools?: boolean
  preferredPlatform?: Platform
  preferredModelId?: string
  skipModels?: Set<string>
}

interface Candidate {
  provider: Provider
  model: ProviderModel
  platform: Platform
}

function buildChain(options: RouteOptions): Candidate[] {
  const candidates: Candidate[] = []

  for (const { platform, provider } of getAllProviders()) {
    for (const model of provider.models) {
      if (options.requireVision && !model.supportsVision) continue
      if (options.requireTools && !model.supportsTools) continue
      if (options.skipModels?.has(`${platform}:${model.id}`)) continue
      candidates.push({ provider, model, platform })
    }
  }

  if (options.preferredPlatform || options.preferredModelId) {
    candidates.sort((a, b) => {
      const aMatch =
        (options.preferredPlatform ? a.platform === options.preferredPlatform : true) &&
        (options.preferredModelId ? a.model.id === options.preferredModelId : true)
      const bMatch =
        (options.preferredPlatform ? b.platform === options.preferredPlatform : true) &&
        (options.preferredModelId ? b.model.id === options.preferredModelId : true)
      return aMatch === bMatch ? 0 : aMatch ? -1 : 1
    })
  }

  return candidates
}

export interface RouteError {
  code: 'no_route'
  message: string
  rejections: Array<{ platform: string; model: string; reason: string }>
}

export function routeRequest(options: RouteOptions = {}): RouteResult & { platform: Platform } {
  const chain = buildChain(options)
  const rejections: RouteError['rejections'] = []

  for (const { provider, model, platform } of chain) {
    const apiKey = getAvailableKey(platform)
    if (!apiKey) {
      rejections.push({ platform, model: model.id, reason: 'no_available_key' })
      continue
    }
    return { provider, modelId: model.id, apiKey, displayName: model.displayName, platform }
  }

  const err: RouteError = {
    code: 'no_route',
    message: 'All models exhausted — check your API key environment variables',
    rejections,
  }
  throw err
}

const RETRY_DEFAULT_MS = 5_000
const MAX_RETRIES = 20

export async function routeWithRetry<T>(
  options: RouteOptions,
  fn: (result: RouteResult & { platform: Platform }) => Promise<T>,
): Promise<T> {
  const skipModels = new Set<string>(options.skipModels)
  let attempt = 0

  while (attempt < MAX_RETRIES) {
    const result = routeRequest({ ...options, skipModels })

    try {
      return await fn(result)
    } catch (err) {
      if (err instanceof ProviderHttpError) {
        if (err.status === 429 || (err.status && err.status >= 500)) {
          const cooldownMs = err.retryAfterMs ?? RETRY_DEFAULT_MS
          setCooldown(result.platform, result.apiKey, cooldownMs)
          skipModels.add(`${result.platform}:${result.modelId}`)
          attempt++
          continue
        }
      }
      throw err
    }
  }

  throw new Error('Max retries exceeded')
}
