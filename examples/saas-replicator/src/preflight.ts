/**
 * Preflight wiring: gather runtime facts (worker list + env) and run the pure
 * `buildPreflightReport` check. Surfaced at boot (index.ts) and as a function
 * (`saas::preflight`) so operators can validate a live deployment.
 */

import type { Engine } from './engine'
import { Logger } from './log'
import { buildPreflightReport, type PreflightReport } from './logic/preflight'

const logger = new Logger(undefined, 'preflight')

export async function runPreflight(engine: Engine): Promise<PreflightReport> {
  const mode = process.env.SAAS_PROVIDER_MODE === 'stub' ? 'stub' : 'live'
  let workers: string[] = []
  try {
    workers = (await engine.listWorkers()).map((w) => w.name).filter(Boolean)
  } catch (err) {
    logger.warn('Could not list workers for preflight', { error: String(err) })
  }
  return buildPreflightReport({ mode, hasAnthropicKey: Boolean(process.env.ANTHROPIC_API_KEY), workers })
}

/** Log the preflight result; problems as warnings, notes as info. */
export function logPreflight(report: PreflightReport): void {
  for (const p of report.problems) logger.warn('preflight', { problem: p })
  for (const n of report.notes) logger.info('preflight', { note: n })
  if (report.ok) logger.info('preflight ok')
}

/** Register `saas::preflight` so a deployment can be validated over the bus. */
export function registerPreflight(engine: Engine): void {
  engine.register('saas::preflight', () => runPreflight(engine), {
    description: 'Validate the runtime configuration (workers + env) before a live run',
    metadata: { tags: ['saas', 'ops'] },
  })
}
