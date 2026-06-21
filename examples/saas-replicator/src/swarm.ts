import { iii } from './iii'
import { Logger } from './log'
import { callRole } from './provider'
import { state } from './state'

const logger = new Logger(undefined, 'swarm')

/**
 * `swarm::ui::analyze-screen` — Phase 1 fan-out consumer. The director enqueues
 * one of these per screenshot onto the `phase1-ui` queue; engine concurrency is
 * the "swarm" (parallel even with a single model). Each result is written under
 * its own state key (scope=`saas/<id>/phase1`) to avoid write contention.
 */
iii.registerFunction(
  'swarm::ui::analyze-screen',
  async (payload: { projectId: string; screen: { id: string; source?: string } }) => {
    const { projectId, screen } = payload
    logger.info('Analyzing screen', { projectId, screen: screen.id })

    const analysis = await callRole('analyzer', [
      {
        role: 'user',
        content: `Analyze this UI screen and extract components, layout and design tokens.`,
        image: screen.source,
      },
    ])

    await state.set({ scope: `saas/${projectId}/phase1`, key: screen.id, value: { screen: screen.id, analysis } })

    // Signal the director; it decides whether Phase 1 is complete.
    await iii.trigger({ function_id: 'director::advance', payload: { projectId } })
    return { ok: true }
  },
  { description: 'Analyze one UI screenshot (Phase 1 swarm worker)', metadata: { tags: ['swarm', 'phase1'] } },
)

/**
 * `swarm::viz::render` — generate a diagram/visual for a spec. Default binding
 * is Claude; with `provider-kimi` present it is auto-rebound to KIMI. Real impl
 * would render via `iii-sandbox`; the skeleton returns the model output.
 */
iii.registerFunction(
  'swarm::viz::render',
  async (payload: { projectId: string; spec: unknown }) => {
    logger.info('Rendering visual', { projectId: payload.projectId })
    const visual = await callRole('visualizer', [
      { role: 'user', content: `Produce a diagram (mermaid) for: ${JSON.stringify(payload.spec)}` },
    ])
    return { visual }
  },
  { description: 'Render a diagram/visual (visualizer role)', metadata: { tags: ['swarm', 'viz'] } },
)

/**
 * `swarm::test::run` — Phase 3 test consumer. Real impl executes the suite in
 * `iii-sandbox`; the skeleton asks the tester role, records the result, and
 * hands control back to the director.
 */
iii.registerFunction(
  'swarm::test::run',
  async (payload: { projectId: string; suite?: unknown }) => {
    const { projectId } = payload
    logger.info('Running tests', { projectId })
    const report = await callRole('tester', [
      { role: 'user', content: `Generate and evaluate tests for the implementation.` },
    ])

    const project = await state.get<Record<string, unknown>>({ scope: `saas/${projectId}`, key: 'project' })
    if (project) {
      const artifacts = { ...((project.artifacts as Record<string, unknown>) ?? {}), tests: report }
      await state.set({ scope: `saas/${projectId}`, key: 'project', value: { ...project, artifacts } })
    }

    await iii.trigger({ function_id: 'director::advance', payload: { projectId } })
    return { ok: true }
  },
  { description: 'Run the test suite (tester role, Phase 3)', metadata: { tags: ['swarm', 'phase3'] } },
)
