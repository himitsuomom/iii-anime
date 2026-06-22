import assert from 'node:assert/strict'
import { test } from 'node:test'
import { MemoryEngine } from '../src/adapters/memoryEngine'
import { startProject } from '../src/director'
import type { Codebase, Prd, ScreenAnalysis, TestReport } from '../src/logic/artifacts'
import type { ProjectState } from '../src/logic/pipeline'
import { registerOrchestrator } from '../src/orchestrator'

process.env.SAAS_PROVIDER_MODE = 'stub'

async function runToCompletion(engine: MemoryEngine, projectId: string): Promise<ProjectState> {
  await engine.drain()
  const proj = await engine.call<ProjectState>('state::get', { scope: `saas/${projectId}`, key: 'project' })
  return proj
}

test('full run with screenshots reaches done with all artifacts (stub mode)', async () => {
  const engine = new MemoryEngine()
  registerOrchestrator(engine)

  const { projectId, status } = await startProject(engine, {
    target: 'Trello',
    requirements: 'JP UI / PWA / responsive',
    screenshots: [{ id: 'board' }, { id: 'card' }, { id: 'modal' }],
  })
  assert.equal(status, 1)

  const proj = await runToCompletion(engine, projectId)
  assert.equal(proj.status, 'done')
  // Every phase produced its artifact.
  assert.ok(proj.artifacts.phase1Review, 'phase1Review present')
  assert.ok(proj.artifacts.prd, 'prd present')
  assert.ok(proj.artifacts.architecture, 'architecture decision present')
  assert.ok(proj.artifacts.implementation, 'implementation present')
  assert.ok(proj.artifacts.tests, 'tests present')
  assert.ok(proj.artifacts.visuals, 'visuals present')
  assert.ok(proj.artifacts.deployment, 'deployment present')

  // The PRD went through the Supervisor review loop.
  const reviews = proj.artifacts.reviews as Record<string, { rounds: number } | undefined>
  assert.ok((reviews?.prd?.rounds ?? 0) >= 1, 'PRD supervised')

  // All three screens were analyzed in Phase 1.
  const analyzed = await engine.call<ScreenAnalysis[]>('state::list', { scope: `saas/${projectId}/phase1` })
  assert.equal(analyzed.length, 3)

  // Artifacts are structured (not raw strings).
  const screen = analyzed[0] as ScreenAnalysis
  assert.ok(Array.isArray(screen.components) && screen.components.length > 0, 'components parsed')
  assert.ok(Array.isArray(screen.tokens.colors) && screen.tokens.colors.length > 0, 'design tokens parsed')

  const prd = proj.artifacts.prd as Prd
  assert.equal(prd.target, 'Trello')
  assert.ok(Array.isArray(prd.features) && prd.features.length > 0, 'PRD features parsed')

  // Phase 3 generated a real codebase and actually executed its test locally.
  const codebase = proj.artifacts.codebase as Codebase
  assert.ok(codebase.files.length > 0, 'codebase files generated')
  const tests = proj.artifacts.tests as TestReport
  assert.equal(tests.viaSandbox, false)
  assert.equal(tests.executor, 'local') // no iii-sandbox worker -> local child process
  assert.ok(tests.total > 0, 'generated test actually ran and reported counts')
  assert.ok((tests.filesGenerated ?? 0) > 0, 'files materialized before running')
})

test('Phase 3 runs tests in iii-sandbox when the worker is present', async () => {
  const engine = new MemoryEngine([{ name: 'iii-sandbox' }])
  registerOrchestrator(engine)
  // Fake sandbox that returns a parseable test summary.
  engine.register('sandbox::run', async () => ({
    stdout: 'TESTS total=3 passed=3 failed=0\n',
    stderr: '',
    exit_code: 0,
    success: true,
  }))

  const { projectId } = await startProject(engine, {
    target: 'Trello',
    requirements: 'x',
    screenshots: [{ id: 'board' }],
  })
  const proj = await runToCompletion(engine, projectId)
  assert.equal(proj.status, 'done')

  const tests = proj.artifacts.tests as TestReport
  assert.equal(tests.viaSandbox, true)
  assert.equal(tests.executor, 'sandbox')
  assert.equal(tests.total, 3)
  assert.equal(tests.passed, 3)
})

test('run with no screenshots skips Phase 1 and still completes', async () => {
  const engine = new MemoryEngine()
  registerOrchestrator(engine)

  const { projectId, status } = await startProject(engine, {
    target: 'Linear',
    requirements: 'minimal',
    screenshots: [],
  })
  assert.equal(status, 2) // jumps straight to PRD

  const proj = await runToCompletion(engine, projectId)
  assert.equal(proj.status, 'done')
  assert.ok(proj.artifacts.prd && proj.artifacts.tests && proj.artifacts.deployment)
})

test('KIMI auto-rebind: analyzer routes to provider-kimi when worker present', async () => {
  // live mode + a registered provider-kimi worker -> analyzer binds to kimi.
  process.env.SAAS_PROVIDER_MODE = 'live'
  try {
    const engine = new MemoryEngine([{ name: 'provider-kimi' }])
    registerOrchestrator(engine)
    // Register stand-in provider workers so live calls resolve in-memory.
    engine.register('provider-anthropic::messages', async () => ({ content: 'claude' }))
    engine.register('provider-kimi::messages', async () => ({ content: 'kimi' }))

    const director = await engine.call('provider::resolve', { role: 'director' })
    const analyzer = await engine.call('provider::resolve', { role: 'analyzer' })
    assert.equal(director.provider, 'anthropic')
    assert.equal(analyzer.provider, 'kimi')
  } finally {
    process.env.SAAS_PROVIDER_MODE = 'stub'
  }
})
