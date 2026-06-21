import assert from 'node:assert/strict'
import { test } from 'node:test'
import { MemoryEngine } from '../src/adapters/memoryEngine'
import { startProject } from '../src/director'
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
  assert.ok(proj.artifacts.implementation, 'implementation present')
  assert.ok(proj.artifacts.tests, 'tests present')
  assert.ok(proj.artifacts.visuals, 'visuals present')
  assert.ok(proj.artifacts.deployment, 'deployment present')

  // All three screens were analyzed in Phase 1.
  const analyzed = await engine.call<unknown[]>('state::list', { scope: `saas/${projectId}/phase1` })
  assert.equal(analyzed.length, 3)
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
