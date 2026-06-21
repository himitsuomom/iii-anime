import { randomUUID } from 'node:crypto'
import { TriggerAction } from 'iii-sdk'
import { useApi } from './hooks'
import { iii } from './iii'
import { Logger } from './log'
import { initialState, type ProjectState, phase1Complete, type StartInput } from './logic/pipeline'
import { callRole } from './provider'
import { state } from './state'

const logger = new Logger(undefined, 'director')

const PROJECT_KEY = 'project'
const projectScope = (id: string) => `saas/${id}`
const phase1Scope = (id: string) => `saas/${id}/phase1`

async function loadProject(id: string): Promise<ProjectState | null> {
  return state.get<ProjectState>({ scope: projectScope(id), key: PROJECT_KEY })
}

async function saveProject(proj: ProjectState): Promise<ProjectState> {
  await state.set({ scope: projectScope(proj.projectId), key: PROJECT_KEY, value: proj })
  return proj
}

/**
 * `director::plan` (HTTP POST /saas/replicate) — entry point. Creates the
 * project, persists initial state, and fans Phase 1 screenshots onto the
 * `phase1-ui` queue (the swarm). With no screenshots it jumps straight to PRD.
 */
useApi<StartInput>(
  {
    api_path: '/saas/replicate',
    http_method: 'POST',
    description: 'Start a SaaS replication run',
    metadata: { tags: ['saas'] },
  },
  async (req, log) => {
    const input = req.body
    if (!input?.target) {
      return { status_code: 400, body: { error: 'target is required' } }
    }
    const projectId = randomUUID()
    const proj = initialState(projectId, {
      target: input.target,
      requirements: input.requirements ?? '',
      screenshots: input.screenshots ?? [],
    })
    await saveProject(proj)
    log.info('Project created', { projectId, screens: proj.phase1.total })

    if (proj.phase1.total > 0) {
      for (const screen of input.screenshots) {
        await iii.trigger({
          function_id: 'swarm::ui::analyze-screen',
          payload: { projectId, screen },
          action: TriggerAction.Enqueue({ queue: 'phase1-ui' }),
        })
      }
    } else {
      await iii.trigger({ function_id: 'director::advance', payload: { projectId } })
    }

    return { status_code: 202, body: { projectId, status: proj.status } }
  },
)

/** `GET /saas/status/:id` — inspect a run's current state. */
useApi(
  {
    api_path: '/saas/status/:id',
    http_method: 'GET',
    description: 'Get replication run status',
    metadata: { tags: ['saas'] },
  },
  async (req) => {
    const id = req.path_params.id
    if (!id) return { status_code: 400, body: { error: 'id is required' } }
    const proj = await loadProject(id)
    if (!proj) return { status_code: 404, body: { error: 'project not found' } }
    const analyzed = (await state.list({ scope: phase1Scope(proj.projectId) })).length
    return { status_code: 200, body: { ...proj, analyzed } }
  },
)

/**
 * `director::advance` — the pipeline driver. Invoked by swarm consumers and by
 * itself. Runs synchronous phases in a loop and returns when it must wait for
 * async swarm work (Phase 1 analysis, Phase 3 tests) or when the run is done.
 */
iii.registerFunction(
  'director::advance',
  async (payload: { projectId: string }) => {
    const { projectId } = payload
    let proj = await loadProject(projectId)
    if (!proj) return { error: 'project not found' }

    while (true) {
      if (proj.status === 'done') return { done: true }

      // Phase 1: wait for the screenshot swarm, then review.
      if (proj.status === 1) {
        const analyzed = (await state.list({ scope: phase1Scope(projectId) })).length
        if (!phase1Complete(proj.phase1.total, analyzed)) {
          return { waiting: 'phase1', analyzed, total: proj.phase1.total }
        }
        logger.info('Phase 1 complete; reviewing', { projectId, analyzed })
        const review = await callRole('director', [
          { role: 'user', content: `Review ${analyzed} screen analyses and outline a PRD for ${proj.target}.` },
        ])
        proj = await saveProject({ ...proj, status: 2, artifacts: { ...proj.artifacts, phase1Review: review } })
        continue
      }

      // Phase 2: PRD (director) + diagrams (visualizer swarm).
      if (proj.status === 2) {
        logger.info('Phase 2: generating PRD', { projectId })
        const prd = await callRole('director', [
          { role: 'user', content: `Write a PRD for ${proj.target}. Requirements: ${proj.requirements}` },
        ])
        await iii.trigger({
          function_id: 'swarm::viz::render',
          payload: { projectId, spec: { kind: 'architecture', target: proj.target } },
          action: TriggerAction.Enqueue({ queue: 'viz' }),
        })
        proj = await saveProject({ ...proj, status: 3, artifacts: { ...proj.artifacts, prd } })
        continue
      }

      // Phase 3: implement (director) then await the test swarm.
      if (proj.status === 3) {
        if (!proj.artifacts.tests) {
          logger.info('Phase 3: implementing, then queuing tests', { projectId })
          const implementation = await callRole('director', [
            { role: 'user', content: `Implement ${proj.target} per the PRD (frontend, backend, auth).` },
          ])
          proj = await saveProject({ ...proj, artifacts: { ...proj.artifacts, implementation } })
          await iii.trigger({
            function_id: 'swarm::test::run',
            payload: { projectId },
            action: TriggerAction.Enqueue({ queue: 'phase3-test' }),
          })
          return { waiting: 'tests' }
        }
        proj = await saveProject({ ...proj, status: 4 })
        continue
      }

      // Phase 4: visualize + (approval) + deploy.
      if (proj.status === 4) {
        logger.info('Phase 4: report and deploy', { projectId })
        const visuals = await callRole('visualizer', [
          { role: 'user', content: `Produce final architecture and test report visuals for ${proj.target}.` },
        ])
        const deployment = await callRole('director', [
          { role: 'user', content: `Prepare deployment + PWA config for ${proj.target}.` },
        ])
        proj = await saveProject({ ...proj, status: 'done', artifacts: { ...proj.artifacts, visuals, deployment } })
        return { done: true }
      }
    }
  },
  { description: 'Drive the 4-phase replication pipeline', metadata: { tags: ['saas'] } },
)
