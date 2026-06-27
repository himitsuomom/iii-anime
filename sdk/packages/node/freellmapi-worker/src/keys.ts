import type { Platform } from './providers/index.js'

export interface KeyEntry {
  platform: Platform
  apiKey: string
  cooldownUntil?: number
}

const cooldowns = new Map<string, number>()

function keyId(platform: Platform, apiKey: string): string {
  return `${platform}:${apiKey}`
}

export function getApiKeys(platform: Platform): string[] {
  const envMap: Partial<Record<Platform, string>> = {
    groq: process.env.GROQ_API_KEY,
    google: process.env.GOOGLE_API_KEY,
    cerebras: process.env.CEREBRAS_API_KEY,
    mistral: process.env.MISTRAL_API_KEY,
    openrouter: process.env.OPENROUTER_API_KEY,
    pollinations: '__keyless__',
    cohere: process.env.COHERE_API_KEY,
  }

  const raw = envMap[platform] ?? ''
  if (!raw) return []

  return raw
    .split(',')
    .map((k) => k.trim())
    .filter(Boolean)
}

export function getAvailableKey(platform: Platform): string | undefined {
  const keys = getApiKeys(platform)
  const now = Date.now()
  for (const key of keys) {
    const cooldown = cooldowns.get(keyId(platform, key))
    if (!cooldown || cooldown <= now) return key
  }
  return undefined
}

export function setCooldown(platform: Platform, apiKey: string, ms: number): void {
  cooldowns.set(keyId(platform, apiKey), Date.now() + ms)
}

export function clearCooldown(platform: Platform, apiKey: string): void {
  cooldowns.delete(keyId(platform, apiKey))
}
