import type { Engine } from './engine'
import { pickExecutor } from './executor'
import { Logger } from './log'
import {
  buildScreenAnalysis,
  type Codebase,
  parseTestStdout,
  type TestReport,
  type VisualArtifact,
} from './logic/artifacts'
import { analyzeScreenPrompt, vizPrompt } from './logic/prompts'
import { callRole, callRoleJson } from './provider'
import { cleanup, createWorkspace, materialize } from './workspace'

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

  // Phase 3 tests. Materializes the generated codebase, then runs its test in
  // iii-sandbox (preferred) or the local child-process executor. With no
  // codebase it falls back to asking the tester role.
  engine.register(
    'swarm::test::run',
    async (payload: { projectId: string }) => {
      const { projectId } = payload
      logger.info('Running tests', { projectId })

      const project = await engine.call<Record<string, unknown> | null>('state::get', {
        scope: `saas/${projectId}`,
        key: 'project',
      })
      const codebase = (project?.artifacts as Record<string, unknown> | undefined)?.codebase as Codebase | undefined

      const report = codebase?.files?.length ? await runGeneratedTests(engine, codebase) : await runTestsViaRole(engine)

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
    { description: 'Run the generated test suite (Phase 3)', metadata: { tags: ['swarm', 'phase3'] } },
  )
}

/** Write the codebase to a temp workspace and run its entry test, then clean up. */
async function runGeneratedTests(engine: Engine, codebase: Codebase): Promise<TestReport> {
  const root = await createWorkspace()
  try {
    const written = await materialize(codebase.files, root)
    const executor = await pickExecutor(engine)
    const testContent = codebase.files.find((f) => f.path === codebase.testFile)?.content ?? ''
    // Pass both: the local executor runs the file (imports resolve via cwd);
    // the sandbox executor runs the inline content.
    const result = await executor.run({ lang: 'node', file: codebase.testFile, code: testContent, cwd: root })
    const report = parseTestStdout(result.stdout ?? '', executor.kind === 'sandbox')
    return { ...report, executor: executor.kind, filesGenerated: written.length }
  } finally {
    await cleanup(root)
  }
}

/** Fallback: ask the tester role for a report when no codebase was generated. */
async function runTestsViaRole(engine: Engine): Promise<TestReport> {
  const raw = await callRole(engine, 'tester', [
    { role: 'user', content: 'Generate and evaluate tests; reply with a short summary.' },
  ])
  return {
    total: 0,
    passed: 0,
    failed: 0,
    viaSandbox: false,
    executor: 'role',
    filesGenerated: 0,
    stdout: typeof raw === 'string' ? raw : JSON.stringify(raw),
  }
}
