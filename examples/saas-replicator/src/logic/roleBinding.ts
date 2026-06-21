/**
 * Pure role-binding logic (no iii-sdk imports — unit-testable in isolation).
 *
 * A "role" is what the orchestrator needs done (director, analyzer, ...). A
 * "provider" is the model worker that actually does it. Roles are
 * provider-agnostic; this module resolves role -> provider at runtime.
 *
 * Default = Claude-only: every role binds to `anthropic`, so the whole
 * pipeline runs end-to-end with only `provider-anthropic` available.
 * When `provider-kimi` is present, analysis/visualization/test roles are
 * auto-rebound to KIMI (progressive enhancement). Explicit overrides win.
 */

export type Role = 'director' | 'analyzer' | 'visualizer' | 'tester' | 'swarm'

export type ProviderKey = 'anthropic' | 'kimi' | 'stub'

export const ALL_ROLES: Role[] = ['director', 'analyzer', 'visualizer', 'tester', 'swarm']

/** Roles handed to KIMI when it is available (Director always stays on Claude). */
export const KIMI_ELIGIBLE_ROLES: Role[] = ['analyzer', 'visualizer', 'tester', 'swarm']

export interface ProviderBinding {
  provider: ProviderKey
  /** iii function_id to invoke, e.g. `provider-anthropic::messages`. */
  functionId: string
  model: string
}

export interface ResolveOptions {
  /** `stub` forces every role onto the in-process mock provider. Default `live`. */
  mode?: 'live' | 'stub'
  /** Whether a `provider-kimi` worker is registered (detected via engine). */
  kimiAvailable?: boolean
  /** Explicit per-role provider overrides from config; these take precedence. */
  overrides?: Partial<Record<Role, ProviderKey>>
  /** Per-provider default model id overrides. */
  models?: Partial<Record<ProviderKey, string>>
}

/** Default model id per provider. Kept generic/current; not pinned to a build. */
export const DEFAULT_MODELS: Record<ProviderKey, string> = {
  anthropic: 'claude-sonnet-4-6',
  kimi: 'kimi-k2',
  stub: 'stub',
}

/** Stable in-process function id used by the bundled mock provider. */
export const STUB_FUNCTION_ID = 'saas::provider::stub'

export function providerFunctionId(provider: ProviderKey): string {
  switch (provider) {
    case 'anthropic':
      return 'provider-anthropic::messages'
    case 'kimi':
      return 'provider-kimi::messages'
    case 'stub':
      return STUB_FUNCTION_ID
  }
}

/**
 * Resolve every role to a concrete provider binding.
 * Precedence: stub mode > explicit override > kimi-when-available > anthropic.
 */
export function resolveBindings(opts: ResolveOptions = {}): Record<Role, ProviderBinding> {
  const mode = opts.mode ?? 'live'
  const models = { ...DEFAULT_MODELS, ...opts.models }
  const overrides = opts.overrides ?? {}

  const pick = (role: Role): ProviderKey => {
    if (mode === 'stub') return 'stub'
    if (overrides[role]) return overrides[role] as ProviderKey
    if (opts.kimiAvailable && KIMI_ELIGIBLE_ROLES.includes(role)) return 'kimi'
    return 'anthropic'
  }

  const out = {} as Record<Role, ProviderBinding>
  for (const role of ALL_ROLES) {
    const provider = pick(role)
    out[role] = { provider, functionId: providerFunctionId(provider), model: models[provider] }
  }
  return out
}

/** Convenience: resolve a single role. */
export function resolveRole(role: Role, opts: ResolveOptions = {}): ProviderBinding {
  return resolveBindings(opts)[role]
}
