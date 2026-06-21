// App-type adapter registry. Build/QA/design code goes through here, never
// hard-coding a specific type.
import type { Plan, Rubric } from '../types.js'
import type { AppTypeAdapter } from './adapter.js'
import { staticWeb } from './static-web.js'
import { webNode } from './web-node.js'

const ADAPTERS = new Map<string, AppTypeAdapter>()

export function register(adapter: AppTypeAdapter): void {
  ADAPTERS.set(adapter.id, adapter)
}

register(webNode)
register(staticWeb)

export function getAdapter(id: string): AppTypeAdapter | undefined {
  return ADAPTERS.get(id)
}

export function adapterIds(): string[] {
  return [...ADAPTERS.keys()]
}

/** The QA rubric for a plan, via its adapter. Falls back to build/test commands. */
export function rubricFor(plan: Plan | undefined): Rubric {
  if (!plan) return { hard: [] }
  const adapter = ADAPTERS.get(plan.app_type)
  if (adapter) return adapter.rubric(plan)
  return {
    hard: [
      { id: 'build', cmd: plan.build_cmd, expect: 'exit0' },
      { id: 'test', cmd: plan.test_cmd, expect: 'exit0' },
    ],
  }
}

/** Extra allowlist entries required by a plan's app type. */
export function extraAllowlistFor(plan: Plan | undefined): string[] {
  if (!plan) return []
  return ADAPTERS.get(plan.app_type)?.extraAllowlist ?? []
}

/** Catalog of app types + guidance, for the design prompt. */
export function designGuidanceBlock(): string {
  return [...ADAPTERS.values()]
    .map((a) => `- "${a.id}" — ${a.title}\n  ${a.designGuidance}`)
    .join('\n')
}
