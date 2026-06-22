import { randomUUID } from 'node:crypto'
import type { Engine, Json } from './engine'
import { Logger } from './log'
import {
  buildCodebase,
  buildDeployment,
  buildPrd,
  type Implementation,
  type Prd,
  type VisualArtifact,
} from './logic/artifacts'
import { initialState, type ProjectState, phase1Complete, type StartInput } from './logic/pipeline'
import { codebasePrompt, deployPrompt, prdPrompt, vizPrompt } from './logic/prompts'
import { debateOrCritique, supervisedGenerate } from './patterns'
import { callRole, callRoleJson } from './provider'

/**
 * Phase 4 human gate. Calls an `approval-gate` worker when present; otherwise
 * auto-approves. The function id below matches the iii-hq/workers harness
 * convention — adjust if your deployed approval worker differs.
 */
async function requestApproval(engine: Engine, projectId: string, summary: string): Promise<boolean> {
  try {
    const workers = await engine.listWorkers()
    if (!workers.some((w) => typeof w?.name === 'string' && w.name.includes('approval-gate'))) return true
    const res = await engine.call<{ approved?: boolean }>('approval-gate::request', { projectId, summary })
    return res?.approved !== false
  } catch {
    return true
  }
}

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

    // Phase 2: PRD (director, supervised) + diagrams (visualizer swarm).
    if (proj.status === 2) {
      logger.info('Phase 2: generating PRD (supervised)', { projectId })
      const { target, requirements } = proj // const snapshot for the prompt closure
      const supervised = await supervisedGenerate<Prd>(engine, {
        role: 'director',
        criticRole: 'director', // self-supervision in Claude-only mode
        target,
        prompt: (feedback) =>
          prdPrompt(target, feedback ? `${requirements}\nReviewer feedback: ${feedback}` : requirements),
        build: (raw) => buildPrd(target, raw),
      })
      await engine.enqueue(
        'swarm::viz::render',
        { projectId, spec: { kind: 'architecture', target: proj.target } },
        'viz',
      )
      proj = await saveProject(engine, {
        ...proj,
        status: 3,
        artifacts: {
          ...proj.artifacts,
          prd: supervised.artifact,
          reviews: {
            ...(proj.artifacts.reviews ?? {}),
            prd: { rounds: supervised.rounds, critiques: supervised.critiques },
          },
        },
      })
      continue
    }

    // Phase 3: decide architecture (debate/self-critique), implement, then test.
    if (proj.status === 3) {
      if (!proj.artifacts.tests) {
        logger.info('Phase 3: architecture decision, implementing, then queuing tests', { projectId })
        const architecture = await debateOrCritique(engine, {
          question: `What architecture should we use to rebuild ${proj.target}?`,
          proposerRole: 'director', // always Claude
          opponentRole: 'swarm', // KIMI when present -> real debate; else self-critique
          judgeRole: 'director',
        })
        // Generate real file contents; the file plan (`implementation`) is the
        // codebase's table of contents (no separate LLM call).
        const codebase = buildCodebase(proj.target, await callRoleJson(engine, 'director', codebasePrompt(proj.target)))
        const implementation: Implementation = { target: proj.target, files: codebase.files.map((f) => f.path) }
        proj = await saveProject(engine, {
          ...proj,
          artifacts: { ...proj.artifacts, architecture, codebase, implementation },
        })
        await engine.enqueue('swarm::test::run', { projectId }, 'phase3-test')
        return { waiting: 'tests' }
      }
      proj = await saveProject(engine, { ...proj, status: 4 })
      continue
    }

    // Phase 4: visualize + approval + deploy.
    if (proj.status === 4) {
      logger.info('Phase 4: report and deploy', { projectId })
      const vizRaw = await callRoleJson(engine, 'visualizer', vizPrompt({ kind: 'final-report', target: proj.target }))
      const visuals: VisualArtifact = {
        format: 'mermaid',
        source: typeof vizRaw.source === 'string' && vizRaw.source ? vizRaw.source : 'graph TD; A-->B',
      }
      const approved = await requestApproval(engine, projectId, `Release ${proj.target}?`)
      if (!approved) {
        proj = await saveProject(engine, { ...proj, artifacts: { ...proj.artifacts, visuals } })
        return { waiting: 'approval' }
      }
      const deployment = buildDeployment(await callRoleJson(engine, 'director', deployPrompt(proj.target)))
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
