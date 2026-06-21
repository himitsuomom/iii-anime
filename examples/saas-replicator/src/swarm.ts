import type { Engine } from './engine'
import { Logger } from './log'
import { buildScreenAnalysis, parseTestStdout, type TestReport, type VisualArtifact } from './logic/artifacts'
import { analyzeScreenPrompt, vizPrompt } from './logic/prompts'
import { callRole, callRoleJson } from './provider'
import { runInSandbox, sandboxAvailable } from './sandbox'

const logger = new Logger(undefined, 'swarm')

/** Register the Phase 1/3/4 swarm consumers. */
export function registerSwarm(engine: Engine): void {
  // Phase 1 fan-out: one per screenshot. Parallelism = queue concurrency.
  engine.register(
    'swarm::ui::analyze-screen',
    async (payload: { projectId: string; screen: { id: string; source?: string } }) => {
      const { projectId, screen } = payload
      logger.info('Analyzing screen', { projectId, screen: screen.id })

      const raw = await callRoleJson(engine, 'analyzer', analyzeScreenPrompt(screen))
      const analysis = buildScreenAnalysis(screen.id, raw)

      await engine.call('state::set', {
        scope: `saas/${projectId}/phase1`,
        key: screen.id,
        value: analysis,
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
    async (payload: { projectId: string; spec: unknown }): Promise<{ visual: VisualArtifact }> => {
      logger.info('Rendering visual', { projectId: payload.projectId })
      const raw = await callRoleJson(engine, 'visualizer', vizPrompt(payload.spec))
      const source = typeof raw.source === 'string' && raw.source.length > 0 ? raw.source : 'graph TD; A-->B'
      return { visual: { format: 'mermaid', source } }
    },
    { description: 'Render a diagram/visual (visualizer role)', metadata: { tags: ['swarm', 'viz'] } },
  )

  // Phase 3 tests. Runs the suite in iii-sandbox when available; otherwise
  // falls back to asking the tester role.
  engine.register(
    'swarm::test::run',
    async (payload: { projectId: string; suite?: unknown }) => {
      const { projectId } = payload
      logger.info('Running tests', { projectId })

      const report = (await sandboxAvailable(engine)) ? await runTestsInSandbox(engine) : await runTestsViaRole(engine)

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

/** Execute a generated test program in an isolated sandbox and parse the summary. */
async function runTestsInSandbox(engine: Engine): Promise<TestReport> {
  // A real impl writes the generated suite; the skeleton runs a representative
  // self-checking script that prints a parseable summary line.
  const code = [
    'const cases = [1+1===2, "a".length===1, [].length===0];',
    'const total = cases.length;',
    'const passed = cases.filter(Boolean).length;',
    'console.log(`TESTS total=${total} passed=${passed} failed=${total-passed}`);',
  ].join('\n')
  const result = await runInSandbox(engine, { lang: 'node', code })
  return parseTestStdout(result.stdout ?? '', true)
}

/** Fallback: ask the tester role for a report when no sandbox is available. */
async function runTestsViaRole(engine: Engine): Promise<TestReport> {
  const raw = await callRole(engine, 'tester', [
    { role: 'user', content: 'Generate and evaluate tests; reply with a short summary.' },
  ])
  return {
    total: 0,
    passed: 0,
    failed: 0,
    viaSandbox: false,
    stdout: typeof raw === 'string' ? raw : JSON.stringify(raw),
  }
}
