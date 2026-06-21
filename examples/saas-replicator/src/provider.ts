import { EngineFunctions } from 'iii-sdk'
import { iii } from './iii'
import { Logger } from './log'
import {
  type ProviderBinding,
  type ResolveOptions,
  type Role,
  resolveRole,
  STUB_FUNCTION_ID,
} from './logic/roleBinding'
import { state } from './state'

const logger = new Logger(undefined, 'provider')

/** Config persisted in iii-state at scope=`config`, key=`role-bindings`. */
interface RoleBindingConfig {
  overrides?: ResolveOptions['overrides']
  models?: ResolveOptions['models']
}

/** Best-effort detection of a registered `provider-kimi` worker. */
async function detectKimi(): Promise<boolean> {
  try {
    const workers = await iii.trigger<unknown, Array<{ name?: string; worker_name?: string }>>({
      function_id: EngineFunctions.LIST_WORKERS,
      payload: {},
    })
    if (!Array.isArray(workers)) return false
    return workers.some((w) => {
      const name = w?.name ?? w?.worker_name ?? ''
      return typeof name === 'string' && name.includes('provider-kimi')
    })
  } catch (err) {
    logger.warn('Could not list workers for KIMI detection; assuming unavailable', { error: String(err) })
    return false
  }
}

async function loadConfig(): Promise<RoleBindingConfig> {
  try {
    return (await state.get<RoleBindingConfig>({ scope: 'config', key: 'role-bindings' })) ?? {}
  } catch {
    return {}
  }
}

/**
 * `provider::resolve` — return the concrete provider binding for a role.
 * Default mode binds everything to Claude (`provider-anthropic`); KIMI is used
 * only when present, and `stub` mode (SAAS_PROVIDER_MODE=stub) routes to the
 * bundled in-process mock so the pipeline runs without any API keys.
 */
iii.registerFunction(
  'provider::resolve',
  async (payload: { role: Role }): Promise<ProviderBinding> => {
    const mode = process.env.SAAS_PROVIDER_MODE === 'stub' ? 'stub' : 'live'
    const cfg = mode === 'stub' ? {} : await loadConfig()
    const kimiAvailable = mode === 'stub' ? false : await detectKimi()
    const binding = resolveRole(payload.role, { mode, kimiAvailable, ...cfg })
    logger.info('Resolved role', { role: payload.role, provider: binding.provider, model: binding.model })
    return binding
  },
  { description: 'Resolve a role (director/analyzer/...) to a provider binding' },
)

/**
 * `saas::provider::stub` — deterministic in-process mock provider. Lets the
 * full 4-phase pipeline run end-to-end with only the engine + built-in workers
 * (no ANTHROPIC_API_KEY, no provider workers).
 */
iii.registerFunction(
  STUB_FUNCTION_ID,
  async (payload: { model?: string; messages?: unknown }) => {
    const summary = JSON.stringify(payload?.messages ?? '').slice(0, 240)
    return {
      content: `[stub:${payload?.model ?? 'stub'}] ${summary}`,
      usage: { input_tokens: 0, output_tokens: 0 },
      stub: true,
    }
  },
  { description: 'Deterministic mock provider used in stub mode' },
)

/** Resolve `role` then invoke the bound provider with the given messages. */
export async function callRole(role: Role, messages: unknown): Promise<unknown> {
  const binding = await iii.trigger<{ role: Role }, ProviderBinding>({
    function_id: 'provider::resolve',
    payload: { role },
  })
  return iii.trigger({
    function_id: binding.functionId,
    payload: { model: binding.model, messages },
  })
}
