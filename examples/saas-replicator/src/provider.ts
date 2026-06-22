import type { Engine } from './engine'
import { Logger } from './log'
import { parseJsonFromContent } from './logic/artifacts'
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
  // Returns JSON keyed off the prompt so the artifact builders get real shapes.
  engine.register(
    STUB_FUNCTION_ID,
    async ({ model, messages }: { model?: string; messages?: unknown }) => {
      const content = stubContent(messages)
      // Rough deterministic token estimate (~4 chars/token) so the budget guard
      // is exercisable in stub mode (e.g. `SAAS_TOKEN_BUDGET=1 npm run demo`).
      const inputChars = JSON.stringify(messages ?? '').length
      return {
        content,
        usage: { input_tokens: Math.ceil(inputChars / 4), output_tokens: Math.ceil(content.length / 4) },
        model: model ?? 'stub',
        stub: true,
      }
    },
    { description: 'Deterministic mock provider used in stub mode' },
  )
}

/** Produce deterministic JSON matching the contract embedded in the prompt. */
function stubContent(messages: unknown): string {
  const text = Array.isArray(messages)
    ? messages
        .map((m) => (m && typeof m === 'object' ? String((m as { content?: unknown }).content ?? '') : ''))
        .join(' ')
    : String(messages ?? '')
  const has = (s: string) => text.toLowerCase().includes(s)

  // Pattern prompts first — these wrap other artifacts, so match before the
  // artifact branches below (which key off words like "features"/"source").
  if (has('critique') || has('quality score')) return JSON.stringify({ score: 0.9, pass: true, feedback: 'looks good' })
  if (has('debate') || has('synthesize') || has('positions'))
    return JSON.stringify({ answer: 'Use a modular monolith with a typed API boundary', rationale: 'simple to ship' })

  if (has('mermaid') || has('"source"')) return JSON.stringify({ source: 'graph TD; A[User]-->B[Director]-->C[Swarm]' })
  if (has('components') || has('tokens'))
    return JSON.stringify({
      components: ['Button', 'Card', 'List'],
      tokens: { colors: ['#ffffff', '#0079bf'], fonts: ['Inter'], spacing: [4, 8, 16] },
      notes: 'stub analysis',
    })
  if (has('features') || has('datamodel'))
    return JSON.stringify({
      summary: 'Stub PRD',
      features: ['boards', 'cards', 'labels'],
      dataModel: ['users', 'boards', 'cards'],
    })
  // Codebase must precede the generic "files" branch (its prompt also says "files").
  if (has('codebase') || has('testfile') || has('runnable'))
    return JSON.stringify({
      files: [
        { path: 'src/app.mjs', content: 'export const add = (a, b) => a + b\n' },
        {
          path: 'test.mjs',
          content:
            "import { add } from './src/app.mjs'\nconst cases = [add(1, 1) === 2, add(2, 2) === 4]\nconst total = cases.length\nconst passed = cases.filter(Boolean).length\nconsole.log('TESTS total=' + total + ' passed=' + passed + ' failed=' + (total - passed))\n",
        },
      ],
      testFile: 'test.mjs',
    })
  if (has('files'))
    return JSON.stringify({ files: ['frontend/app.tsx', 'backend/api.ts', 'backend/auth.ts'], notes: 'stub impl' })
  if (has('pwa') || has('deployment') || has('"url"'))
    return JSON.stringify({ url: 'https://stub.local', pwa: true, notes: 'stub deploy' })
  return JSON.stringify({ note: 'stub' })
}

/** Resolve `role` then invoke the bound provider with the given messages. */
export async function callRole(engine: Engine, role: Role, messages: unknown): Promise<unknown> {
  const binding = await engine.call<ProviderBinding>('provider::resolve', { role })
  return engine.call(binding.functionId, { model: binding.model, messages })
}

/** Like `callRole`, but parses the provider response into a JSON object. */
export async function callRoleJson(engine: Engine, role: Role, messages: unknown): Promise<Record<string, unknown>> {
  return parseJsonFromContent(await callRole(engine, role, messages))
}
