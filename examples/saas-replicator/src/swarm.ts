import type { Engine } from './engine'
import { Logger } from './log'
import { callRole } from './provider'

const logger = new Logger(undefined, 'swarm')

/** Register the Phase 1/3/4 swarm consumers. */
export function registerSwarm(engine: Engine): void {
  // Phase 1 fan-out: one per screenshot. Parallelism = queue concurrency.
  engine.register(
    'swarm::ui::analyze-screen',
    async (payload: { projectId: string; screen: { id: string; source?: string } }) => {
      const { projectId, screen } = payload
      logger.info('Analyzing screen', { projectId, screen: screen.id })

      const analysis = await callRole(engine, 'analyzer', [
        {
          role: 'user',
          content: 'Analyze this UI screen and extract components, layout and design tokens.',
          image: screen.source,
        },
      ])

      await engine.call('state::set', {
        scope: `saas/${projectId}/phase1`,
        key: screen.id,
        value: { screen: screen.id, analysis },
      })

      // Signal the director; it decides whether Phase 1 is complete.
      await engine.call('director::advance', { projectId })
      return { ok: true }
    },
    { description: 'Analyze one UI screenshot (Phase 1 swarm worker)', metadata: { tags: ['swarm', 'phase1'] } },
  )

  // Diagram/visual generation (visualizer role; auto-rebound to KIMI if present).
  engine.register(
    'swarm::viz::render',
    async (payload: { projectId: string; spec: unknown }) => {
      logger.info('Rendering visual', { projectId: payload.projectId })
      const visual = await callRole(engine, 'visualizer', [
        { role: 'user', content: `Produce a diagram (mermaid) for: ${JSON.stringify(payload.spec)}` },
      ])
      return { visual }
    },
    { description: 'Render a diagram/visual (visualizer role)', metadata: { tags: ['swarm', 'viz'] } },
  )

  // Phase 3 tests. Real impl runs the suite in iii-sandbox; skeleton asks the role.
  engine.register(
    'swarm::test::run',
    async (payload: { projectId: string; suite?: unknown }) => {
      const { projectId } = payload
      logger.info('Running tests', { projectId })
      const report = await callRole(engine, 'tester', [
        { role: 'user', content: 'Generate and evaluate tests for the implementation.' },
      ])

      const project = await engine.call<Record<string, unknown> | null>('state::get', {
        scope: `saas/${projectId}`,
        key: 'project',
      })
      if (project) {
        const artifacts = { ...((project.artifacts as Record<string, unknown>) ?? {}), tests: report }
        await engine.call('state::set', {
          scope: `saas/${projectId}`,
          key: 'project',
          value: { ...project, artifacts },
        })
      }

      await engine.call('director::advance', { projectId })
      return { ok: true }
    },
    { description: 'Run the test suite (tester role, Phase 3)', metadata: { tags: ['swarm', 'phase3'] } },
  )
}
