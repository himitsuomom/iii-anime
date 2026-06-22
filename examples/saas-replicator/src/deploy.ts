/**
 * Deploy wiring: execute a `DeployPlan` against a real deploy worker when one
 * is registered, otherwise simulate locally. Mirrors the executor pattern —
 * the orchestrator does not care whether deployment is real or simulated.
 */

import type { Engine } from './engine'
import { Logger } from './log'
import type { Codebase, Deployment } from './logic/artifacts'
import { buildDeployPlan } from './logic/deploy'

const logger = new Logger(undefined, 'deploy')

/** Detect a deploy worker (e.g. `deploy`, `vercel`, `netlify`) on the bus. */
async function deployWorker(engine: Engine): Promise<string | null> {
  try {
    const workers = await engine.listWorkers()
    const match = workers.find((w) => typeof w?.name === 'string' && /deploy|vercel|netlify/i.test(w.name))
    return match?.name ?? null
  } catch {
    return null
  }
}

/**
 * Build a plan from the codebase and run it. With a deploy worker present we
 * hand the plan to `<worker>::publish` and trust its returned URL; otherwise we
 * simulate and return a local URL. Always returns a well-formed Deployment.
 */
export async function deploy(engine: Engine, codebase: Codebase): Promise<Deployment> {
  const plan = buildDeployPlan(codebase)
  const worker = await deployWorker(engine)

  if (worker) {
    logger.info('Publishing via deploy worker', { worker, files: plan.files.length })
    try {
      const res = await engine.call<{ url?: string }>(`${worker}::publish`, { plan })
      return {
        url: typeof res?.url === 'string' ? res.url : `https://${slug(plan.target)}.example.app`,
        pwa: true,
        status: 'deployed',
        steps: plan.steps,
        entrypoint: plan.entrypoint,
      }
    } catch (err) {
      logger.warn('Deploy worker failed; simulating', { error: String(err) })
    }
  }

  logger.info('Simulating deployment (no deploy worker)', { files: plan.files.length })
  return {
    url: `https://${slug(plan.target)}.local`,
    pwa: true,
    status: 'simulated',
    steps: plan.steps,
    entrypoint: plan.entrypoint,
    notes: 'simulated — add a deploy worker (deploy/vercel/netlify) to publish for real',
  }
}

function slug(s: string): string {
  return (
    s
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-+|-+$/g, '') || 'app'
  )
}
