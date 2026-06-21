import { randomUUID } from 'node:crypto'
import type { Engine, Json } from './engine'
import { Logger } from './log'
import { initialState, type ProjectState, phase1Complete, type StartInput } from './logic/pipeline'
import { callRole } from './provider'

const logger = new Logger(undefined, 'director')

const PROJECT_KEY = 'project'
const projectScope = (id: string) => `saas/${id}`
const phase1Scope = (id: string) => `saas/${id}/phase1`

async function loadProject(engine: Engine, id: string): Promise<ProjectState | null> {
  return engine.call<ProjectState | null>('state::get', { scope: projectScope(id), key: PROJECT_KEY })
}

async function saveProject(engine: Engine, proj: ProjectState): Promise<ProjectState> {
  await engine.call('state::set', { scope: projectScope(proj.projectId), key: PROJECT_KEY, value: proj })
  return proj
}

async function analyzedCount(engine: Engine, id: string): Promise<number> {
  const items = await engine.call<unknown[]>('state::list', { scope: phase1Scope(id) })
  return Array.isArray(items) ? items.length : 0
}

/**
 * Entry point: create the project, persist initial state, and fan Phase 1
 * screenshots onto the `phase1-ui` queue (the swarm). With no screenshots it
 * jumps straight to the PRD phase.
 */
export async function startProject(
  engine: Engine,
  input: StartInput,
): Promise<{ projectId: string; status: ProjectState['status'] }> {
  const projectId = randomUUID()
  const proj = initialState(projectId, {
    target: input.target,
    requirements: input.requirements ?? '',
    screenshots: input.screenshots ?? [],
  })
  await saveProject(engine, proj)
  logger.info('Project created', { projectId, screens: proj.phase1.total })

  if (proj.phase1.total > 0) {
    for (const screen of input.screenshots) {
      await engine.enqueue('swarm::ui::analyze-screen', { projectId, screen }, 'phase1-ui')
    }
  } else {
    await engine.call('director::advance', { projectId })
  }
  return { projectId, status: proj.status }
}

/**
 * Pipeline driver. Invoked by swarm consumers and by itself. Runs synchronous
 * phases in a loop; returns when it must wait for async swarm work (Phase 1
 * analysis, Phase 3 tests) or when the run is done.
 */
export async function advance(engine: Engine, projectId: string): Promise<Json> {
  let proj = await loadProject(engine, projectId)
  if (!proj) return { error: 'project not found' }

  while (true) {
    if (proj.status === 'done') return { done: true }

    // Phase 1: wait for the screenshot swarm, then review.
    if (proj.status === 1) {
      const analyzed = await analyzedCount(engine, projectId)
      if (!phase1Complete(proj.phase1.total, analyzed)) {
        return { waiting: 'phase1', analyzed, total: proj.phase1.total }
      }
      logger.info('Phase 1 complete; reviewing', { projectId, analyzed })
      const review = await callRole(engine, 'director', [
        { role: 'user', content: `Review ${analyzed} screen analyses and outline a PRD for ${proj.target}.` },
      ])
      proj = await saveProject(engine, { ...proj, status: 2, artifacts: { ...proj.artifacts, phase1Review: review } })
      continue
    }

    // Phase 2: PRD (director) + diagrams (visualizer swarm).
    if (proj.status === 2) {
      logger.info('Phase 2: generating PRD', { projectId })
      const prd = await callRole(engine, 'director', [
        { role: 'user', content: `Write a PRD for ${proj.target}. Requirements: ${proj.requirements}` },
      ])
      await engine.enqueue(
        'swarm::viz::render',
        { projectId, spec: { kind: 'architecture', target: proj.target } },
        'viz',
      )
      proj = await saveProject(engine, { ...proj, status: 3, artifacts: { ...proj.artifacts, prd } })
      continue
    }

    // Phase 3: implement (director) then await the test swarm.
    if (proj.status === 3) {
      if (!proj.artifacts.tests) {
        logger.info('Phase 3: implementing, then queuing tests', { projectId })
        const implementation = await callRole(engine, 'director', [
          { role: 'user', content: `Implement ${proj.target} per the PRD (frontend, backend, auth).` },
        ])
        proj = await saveProject(engine, { ...proj, artifacts: { ...proj.artifacts, implementation } })
        await engine.enqueue('swarm::test::run', { projectId }, 'phase3-test')
        return { waiting: 'tests' }
      }
      proj = await saveProject(engine, { ...proj, status: 4 })
      continue
    }

    // Phase 4: visualize + (approval) + deploy.
    if (proj.status === 4) {
      logger.info('Phase 4: report and deploy', { projectId })
      const visuals = await callRole(engine, 'visualizer', [
        { role: 'user', content: `Produce final architecture and test report visuals for ${proj.target}.` },
      ])
      const deployment = await callRole(engine, 'director', [
        { role: 'user', content: `Prepare deployment + PWA config for ${proj.target}.` },
      ])
      proj = await saveProject(engine, {
        ...proj,
        status: 'done',
        artifacts: { ...proj.artifacts, visuals, deployment },
      })
      return { done: true }
    }
  }
}

/** Register the director functions + HTTP entry points. */
export function registerDirector(engine: Engine): void {
  engine.register('director::advance', ({ projectId }: { projectId: string }) => advance(engine, projectId), {
    description: 'Drive the 4-phase replication pipeline',
    metadata: { tags: ['saas'] },
  })

  // HTTP: start a run.
  engine.register(
    'saas::start',
    async (req: { body?: StartInput } & Partial<StartInput>) => {
      const input = (req?.body ?? req) as StartInput
      if (!input?.target) return { status_code: 400, body: { error: 'target is required' } }
      const result = await startProject(engine, input)
      return { status_code: 202, body: result }
    },
    {
      description: 'Start a SaaS replication run',
      http: { path: '/saas/replicate', method: 'POST' },
      metadata: { tags: ['saas'] },
    },
  )

  // HTTP: inspect a run.
  engine.register(
    'saas::status',
    async (req: { path_params?: { id?: string } }) => {
      const id = req?.path_params?.id
      if (!id) return { status_code: 400, body: { error: 'id is required' } }
      const proj = await loadProject(engine, id)
      if (!proj) return { status_code: 404, body: { error: 'project not found' } }
      const analyzed = await analyzedCount(engine, id)
      return { status_code: 200, body: { ...proj, analyzed } }
    },
    {
      description: 'Get replication run status',
      http: { path: '/saas/status/:id', method: 'GET' },
      metadata: { tags: ['saas'] },
    },
  )
}
