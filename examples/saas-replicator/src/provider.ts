import type { Engine } from './engine'
import { Logger } from './log'
import {
  type ProviderBinding,
  type ResolveOptions,
  type Role,
  resolveRole,
  STUB_FUNCTION_ID,
} from './logic/roleBinding'

const logger = new Logger(undefined, 'provider')

/** Config persisted in iii-state at scope=`config`, key=`role-bindings`. */
interface RoleBindingConfig {
  overrides?: ResolveOptions['overrides']
  models?: ResolveOptions['models']
}

function mode(): 'live' | 'stub' {
  return process.env.SAAS_PROVIDER_MODE === 'stub' ? 'stub' : 'live'
}

async function detectKimi(engine: Engine): Promise<boolean> {
  try {
    const workers = await engine.listWorkers()
    return workers.some((w) => typeof w?.name === 'string' && w.name.includes('provider-kimi'))
  } catch (err) {
    logger.warn('Could not list workers for KIMI detection; assuming unavailable', { error: String(err) })
    return false
  }
}

async function loadConfig(engine: Engine): Promise<RoleBindingConfig> {
  try {
    return (await engine.call<RoleBindingConfig | null>('state::get', { scope: 'config', key: 'role-bindings' })) ?? {}
  } catch {
    return {}
  }
}

/** Register `provider::resolve` and the bundled `saas::provider::stub`. */
export function registerProvider(engine: Engine): void {
  // `provider::resolve` — role -> concrete provider binding. Default Claude-only.
  engine.register(
    'provider::resolve',
    async ({ role }: { role: Role }): Promise<ProviderBinding> => {
      const m = mode()
      const cfg = m === 'stub' ? {} : await loadConfig(engine)
      const kimiAvailable = m === 'stub' ? false : await detectKimi(engine)
      const binding = resolveRole(role, { mode: m, kimiAvailable, ...cfg })
      logger.info('Resolved role', { role, provider: binding.provider, model: binding.model })
      return binding
    },
    { description: 'Resolve a role (director/analyzer/...) to a provider binding' },
  )

  // Deterministic in-process mock provider for stub mode (no API keys needed).
  engine.register(
    STUB_FUNCTION_ID,
    async ({ model, messages }: { model?: string; messages?: unknown }) => ({
      content: `[stub:${model ?? 'stub'}] ${JSON.stringify(messages ?? '').slice(0, 240)}`,
      usage: { input_tokens: 0, output_tokens: 0 },
      stub: true,
    }),
    { description: 'Deterministic mock provider used in stub mode' },
  )
}

/** Resolve `role` then invoke the bound provider with the given messages. */
export async function callRole(engine: Engine, role: Role, messages: unknown): Promise<unknown> {
  const binding = await engine.call<ProviderBinding>('provider::resolve', { role })
  return engine.call(binding.functionId, { model: binding.model, messages })
}
