// app-studio worker entrypoint. Registers the sandbox functions, the HTTP
// intake, and the orchestrator runner with the iii engine. Run via the engine
// (see app-studio/local.yml) — needs `iii-sdk` installed and a running engine.
//
// Brain + build backend default to the local Claude Code CLI, so this runs
// with the machine's existing Claude Code login (no ANTHROPIC_API_KEY). See
// app-studio/BUILD-BACKENDS.md.
import { registerWorker, TriggerAction } from 'iii-sdk'
import { ClaudeCliBrain } from './brain/claude-cli-brain.js'
import { buildBackendFromEnv } from './build/factory.js'
import { advance } from './orchestrator/apply.js'
import type { StudioDeps } from './pipeline/handlers.js'
import { IiiStore } from './runtime/iii-store.js'
import { initialProjectState } from './runtime/store.js'
import { editInWorkspace } from './sandbox/edit.js'
import { execInWorkspace } from './sandbox/exec.js'
import { ensureWorkspace, workspaceDir } from './sandbox/workspace.js'
import { DEFAULT_MAX_ITERATIONS } from './types.js'

const iii = registerWorker(process.env.III_URL ?? 'ws://localhost:49134')

const deps: StudioDeps = {
  store: new IiiStore(iii),
  brain: new ClaudeCliBrain(),
  build: await buildBackendFromEnv(),
  buildMaxTurns: Number(process.env.STUDIO_BUILD_MAX_TURNS ?? 60),
}

// --- sandbox (case A foundation; also used by QA and the future API backend) ---
iii.registerFunction('sandbox::exec', (input) => execInWorkspace(input as never))
iii.registerFunction('sandbox::edit', (input) => editInWorkspace(input as never))

// --- orchestrator: drive the whole pipeline for one project ---
iii.registerFunction('studio::orch::run', async (input) => {
  const { project_id } = input as { project_id: string }
  await advance(deps, project_id, { type: 'project.created' })
  const s = await deps.store.get(project_id)
  return { project_id, status: s?.status, artifacts: s?.artifacts, last_qa: s?.last_qa }
})

// --- HTTP intake: POST /projects { idea } -> 202 { project_id } ---
iii.registerFunction('studio::intake::create', async (input) => {
  const body = (input as { body?: { idea?: string; project_id?: string } }).body ?? {}
  if (!body.idea) return { status_code: 400, body: { error: 'idea is required' } }

  // Minimal idempotency: a provided, existing project_id returns as-is.
  if (body.project_id) {
    const existing = await deps.store.get(body.project_id)
    if (existing) return { status_code: 200, body: { project_id: existing.project_id } }
  }

  const project_id = body.project_id ?? `prj_${Date.now().toString(36)}${Math.random().toString(36).slice(2, 8)}`
  await ensureWorkspace(project_id)
  await deps.store.set(
    initialProjectState(project_id, body.idea, workspaceDir(project_id), DEFAULT_MAX_ITERATIONS),
  )
  // Fire-and-forget: return immediately, run the pipeline in the background.
  iii.trigger({
    function_id: 'studio::orch::run',
    payload: { project_id },
    action: TriggerAction.Void(),
  })
  return { status_code: 202, body: { project_id } }
})

iii.registerTrigger({
  type: 'http',
  function_id: 'studio::intake::create',
  config: { api_path: '/projects', http_method: 'POST' },
})

// --- DX: inspect projects ---
iii.registerFunction('studio::project::get', async (input) => {
  const id = (input as { path_params?: { id?: string } }).path_params?.id
  if (!id) return { status_code: 400, body: { error: 'id required' } }
  const s = await deps.store.get(id)
  if (!s) return { status_code: 404, body: { error: 'not found' } }
  return { status_code: 200, body: s }
})
iii.registerTrigger({
  type: 'http',
  function_id: 'studio::project::get',
  config: { api_path: '/projects/:id', http_method: 'GET' },
})

iii.registerFunction('studio::project::list', async () => {
  const all = await deps.store.list()
  const summary = all
    .map((s) => ({
      project_id: s.project_id,
      status: s.status,
      iteration: s.iteration,
      goal: s.spec?.goal,
      app_type: s.plan?.app_type,
      passed: s.last_qa?.passed,
      updated_at: s.updated_at,
    }))
    .sort((a, b) => (a.updated_at < b.updated_at ? 1 : -1))
  return { status_code: 200, body: { projects: summary } }
})
iii.registerTrigger({
  type: 'http',
  function_id: 'studio::project::list',
  config: { api_path: '/projects', http_method: 'GET' },
})

// eslint-disable-next-line no-console
console.log('app-studio worker registered (sandbox::*, studio::intake::create, studio::orch::run)')
