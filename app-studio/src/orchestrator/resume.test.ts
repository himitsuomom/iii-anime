import assert from 'node:assert/strict'
import { mkdtemp, rm } from 'node:fs/promises'
import os from 'node:os'
import path from 'node:path'
import { afterEach, beforeEach, describe, test } from 'node:test'
import type { BuildBackend, BuildOutcome, BuildRequest } from '../build/backend.js'
import type { Brain, JsonRequest } from '../brain/brain.js'
import { editInWorkspace } from '../sandbox/edit.js'
import { workspaceDir } from '../sandbox/workspace.js'
import { MemoryStore, initialProjectState } from '../runtime/store.js'
import { projectIdFromKey, randomProjectId } from '../runtime/idempotency.js'
import type { StudioDeps } from '../pipeline/handlers.js'
import type { Plan, Spec } from '../types.js'
import { resume, sweep } from './resume.js'

let base: string
beforeEach(async () => {
  base = await mkdtemp(path.join(os.tmpdir(), 'studio-resume-'))
  process.env.STUDIO_WORK_ROOT = base
})
afterEach(async () => {
  await rm(base, { recursive: true, force: true })
  delete process.env.STUDIO_WORK_ROOT
})

const SPEC: Spec = { goal: 'g', features: ['f'], acceptance: ['a'], assumptions: ['x'] }
const PLAN: Plan = {
  app_type: 'web-node',
  stack: ['node'],
  tasks: [],
  build_cmd: 'true',
  test_cmd: 'true',
}
class FakeBrain implements Brain {
  readonly id = 'fake'
  async json<T>(req: JsonRequest<T>): Promise<T> {
    return req.validate(req.user.includes('plan') ? PLAN : SPEC)
  }
}
class FakeBuild implements BuildBackend {
  readonly id = 'fake'
  async run(req: BuildRequest): Promise<BuildOutcome> {
    await editInWorkspace({ project_id: req.project_id, command: 'create', path: 'app.js', file_text: '1\n' })
    return { ok: true, summary: '' }
  }
}
function deps(): StudioDeps {
  return { store: new MemoryStore(), brain: new FakeBrain(), build: new FakeBuild(), buildMaxTurns: 2 }
}

describe('idempotency helpers', () => {
  test('same key -> same project id, different key -> different', () => {
    assert.equal(projectIdFromKey('abc'), projectIdFromKey('abc'))
    assert.notEqual(projectIdFromKey('abc'), projectIdFromKey('def'))
    assert.match(projectIdFromKey('abc'), /^prj_[0-9a-f]{16}$/)
    assert.match(randomProjectId(), /^prj_/)
  })
})

describe('resume', () => {
  test('drives a project stuck mid-pipeline to delivered', async () => {
    const d = deps()
    const pid = 'prj_stuck'
    // Seed as if it crashed right after entering "design".
    await d.store.set({ ...initialProjectState(pid, 'idea', workspaceDir(pid), 5), status: 'design', spec: SPEC })

    const did = await resume(d, pid)
    assert.equal(did, true)
    const final = await d.store.get(pid)
    assert.equal(final?.status, 'delivered')
  })

  test('is a no-op on terminal projects', async () => {
    const d = deps()
    const pid = 'prj_done'
    await d.store.set({ ...initialProjectState(pid, 'i', workspaceDir(pid), 5), status: 'delivered' })
    assert.equal(await resume(d, pid), false)
  })
})

describe('sweep', () => {
  test('resumes stuck non-terminal projects, skips fresh and terminal', async () => {
    const d = deps()
    // stuck (old updated_at), in qa with a passing plan
    await d.store.set({
      ...initialProjectState('prj_old', 'i', workspaceDir('prj_old'), 5),
      status: 'qa',
      spec: SPEC,
      plan: PLAN,
      updated_at: new Date(Date.now() - 10 * 60_000).toISOString(),
    })
    // terminal — must be skipped
    await d.store.set({ ...initialProjectState('prj_term', 'i', workspaceDir('prj_term'), 5), status: 'failed' })

    const resumed = await sweep(d, { stuckMs: 60_000 })
    assert.deepEqual(resumed, ['prj_old'])
    assert.equal((await d.store.get('prj_old'))?.status, 'delivered')
    assert.equal((await d.store.get('prj_term'))?.status, 'failed')
  })
})
