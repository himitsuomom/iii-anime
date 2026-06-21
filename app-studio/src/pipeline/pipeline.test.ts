import assert from 'node:assert/strict'
import { mkdtemp, rm } from 'node:fs/promises'
import os from 'node:os'
import path from 'node:path'
import { afterEach, beforeEach, describe, test } from 'node:test'
import type { BuildBackend, BuildOutcome, BuildRequest } from '../build/backend.js'
import type { Brain, JsonRequest } from '../brain/brain.js'
import { advance } from '../orchestrator/apply.js'
import { editInWorkspace } from '../sandbox/edit.js'
import { workspaceDir } from '../sandbox/workspace.js'
import { MemoryStore, initialProjectState } from '../runtime/store.js'
import { MemoryWikiStore } from '../wiki/wiki-store.js'
import type { Plan, Spec } from '../types.js'
import type { StudioDeps } from './handlers.js'

let base: string
beforeEach(async () => {
  base = await mkdtemp(path.join(os.tmpdir(), 'studio-pipe-'))
  process.env.STUDIO_WORK_ROOT = base
})
afterEach(async () => {
  await rm(base, { recursive: true, force: true })
  delete process.env.STUDIO_WORK_ROOT
})

// FakeBrain returns canned spec/plan, selected by the handler's prompt text.
class FakeBrain implements Brain {
  readonly id = 'fake'
  constructor(
    private spec: Spec,
    private plan: Plan,
  ) {}
  async json<T>(req: JsonRequest<T>): Promise<T> {
    const payload = req.user.includes('Produce the plan') ? this.plan : this.spec
    return req.validate(payload)
  }
  async text(): Promise<string> {
    return '# wiki\nstub'
  }
}

// FakeBuildBackend writes a known file into the workdir and records call count.
class FakeBuildBackend implements BuildBackend {
  readonly id = 'fake-build'
  calls = 0
  lastUserPrompt = ''
  async run(req: BuildRequest): Promise<BuildOutcome> {
    this.calls++
    this.lastUserPrompt = req.userPrompt
    await editInWorkspace({
      project_id: req.project_id,
      command: 'create',
      path: 'app.js',
      file_text: 'console.log("hello")\n',
    })
    return { ok: true, summary: 'wrote app.js' }
  }
}

const SPEC: Spec = {
  goal: 'A tiny web app',
  features: ['prints hello'],
  acceptance: ['app.js exists'],
  assumptions: ['node runtime'],
}
const planWith = (build_cmd: string, test_cmd: string): Plan => ({
  app_type: 'web-node',
  stack: ['node'],
  tasks: ['create app.js'],
  build_cmd,
  test_cmd,
})

function makeDeps(brain: Brain, build: BuildBackend): StudioDeps {
  return { store: new MemoryStore(), brain, build, buildMaxTurns: 4 }
}

describe('pipeline end-to-end (fakes + real sandbox)', () => {
  test('idea -> spec -> plan -> build -> qa(pass) -> delivered', async () => {
    const build = new FakeBuildBackend()
    const deps = makeDeps(new FakeBrain(SPEC, planWith('true', 'true')), build)
    const pid = 'prj_ok'
    await deps.store.set(initialProjectState(pid, 'a tiny web app', workspaceDir(pid), 5))

    await advance(deps, pid, { type: 'project.created' })

    const final = await deps.store.get(pid)
    assert.equal(final?.status, 'delivered')
    assert.deepEqual(final?.spec, SPEC)
    assert.equal(final?.plan?.test_cmd, 'true')
    assert.ok(final?.artifacts?.files.includes('app.js'))
    assert.equal(final?.last_qa?.passed, true)
    assert.equal(build.calls, 1)
  })

  test('failing tests loop until max_iterations then fail', async () => {
    const build = new FakeBuildBackend()
    // build_cmd passes, test_cmd always fails -> qa.failed every round
    const deps = makeDeps(new FakeBrain(SPEC, planWith('true', 'test -f never_exists')), build)
    const pid = 'prj_fail'
    await deps.store.set(initialProjectState(pid, 'doomed', workspaceDir(pid), 2))

    await advance(deps, pid, { type: 'project.created' })

    const final = await deps.store.get(pid)
    assert.equal(final?.status, 'failed')
    assert.equal(final?.last_qa?.passed, false)
    // 2 build attempts (initial + one revision) before hitting the cap.
    assert.equal(build.calls, 2)
  })

  test('require_approval pauses at awaiting_approval, then approve -> delivered', async () => {
    const build = new FakeBuildBackend()
    const deps = makeDeps(new FakeBrain(SPEC, planWith('true', 'true')), build)
    const pid = 'prj_appr'
    await deps.store.set({
      ...initialProjectState(pid, 'x', workspaceDir(pid), 5),
      require_approval: true,
    })

    await advance(deps, pid, { type: 'project.created' })
    let s = await deps.store.get(pid)
    assert.equal(s?.status, 'awaiting_approval')
    assert.equal(build.calls, 1)

    await advance(deps, pid, { type: 'approved' })
    s = await deps.store.get(pid)
    assert.equal(s?.status, 'delivered')
  })

  test('relevant wiki knowledge is fed into the build prompt', async () => {
    const build = new FakeBuildBackend()
    const wiki = new MemoryWikiStore()
    await wiki.put({
      slug: 'app-health',
      title: 'Health endpoint server',
      content: 'A node:http server exposing GET /health returning {status:ok}.',
      source_project_id: 'prj_old',
      created_at: 'now',
      updated_at: 'now',
    })
    const deps: StudioDeps = {
      store: new MemoryStore(),
      brain: new FakeBrain(
        { goal: 'a health endpoint', features: ['/health'], acceptance: ['200'], assumptions: [] },
        planWith('true', 'true'),
      ),
      build,
      wiki,
      buildMaxTurns: 4,
    }
    const pid = 'prj_reuse'
    await deps.store.set(initialProjectState(pid, 'a health endpoint server', workspaceDir(pid), 5))

    await advance(deps, pid, { type: 'project.created' })

    assert.match(build.lastUserPrompt, /prior work/i)
    assert.match(build.lastUserPrompt, /Health endpoint server \(app-health\)/)
    // its own future page (same project) must never be fed back in — n/a here,
    // but the source filter is exercised by excluding prj_reuse.
  })

  test('duplicate project.created after delivery is a no-op', async () => {
    const build = new FakeBuildBackend()
    const deps = makeDeps(new FakeBrain(SPEC, planWith('true', 'true')), build)
    const pid = 'prj_dup'
    await deps.store.set(initialProjectState(pid, 'x', workspaceDir(pid), 5))
    await advance(deps, pid, { type: 'project.created' })
    const steps = await advance(deps, pid, { type: 'project.created' })
    assert.equal(steps, 0) // terminal state absorbs the duplicate
    assert.equal(build.calls, 1)
  })
})
