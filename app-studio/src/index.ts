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
import { sweep } from './orchestrator/resume.js'
import type { StudioDeps } from './pipeline/handlers.js'
import { IiiStore } from './runtime/iii-store.js'
import { projectIdFromKey, randomProjectId } from '../../studio-core/src/idempotency.js'
import { initialProjectState } from './runtime/store.js'
import { IiiWikiStore } from './wiki/iii-wiki-store.js'
import { askWiki } from './wiki/wiki.js'
import { editInWorkspace } from '../../studio-core/src/sandbox/edit.js'
import { execInWorkspace } from '../../studio-core/src/sandbox/exec.js'
import { ensureWorkspace, workspaceDir } from '../../studio-core/src/sandbox/workspace.js'
import { DEFAULT_MAX_ITERATIONS } from './types.js'

import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { checkAuth, unauthorizedResponse } from '../../studio-core/src/auth.js'
import { LeaderLock, RedisCliLockBackend } from '../../studio-core/src/leader.js'
import { detectAlerts } from '../../studio-core/src/alerts.js'

const iii = registerWorker(process.env.III_URL ?? 'ws://localhost:49134')

// Self-contained dashboard UI, served by the worker. (A panel that can later be
// embedded into the iii Console SPA; standalone here for zero-build operation.)
const DASHBOARD_HTML = (() => {
  try {
    return readFileSync(fileURLToPath(new URL('../ui/dashboard.html', import.meta.url)), 'utf8')
  } catch {
    return '<!doctype html><title>iii App Studio</title><p>dashboard.html not found</p>'
  }
})()

const brain = new ClaudeCliBrain()
const wiki = new IiiWikiStore(iii)
const deps: StudioDeps = {
  store: new IiiStore(iii),
  brain,
  build: await buildBackendFromEnv(),
  wiki,
  buildMaxTurns: Number(process.env.STUDIO_BUILD_MAX_TURNS ?? 60),
  maxCostUsd: process.env.STUDIO_MAX_COST_USD ? Number(process.env.STUDIO_MAX_COST_USD) : undefined,
}

// Concurrency: when STUDIO_BUILD_QUEUE is set, pipelines run through that named
// queue (per-factory concurrency via the queue's config) instead of inline.
const BUILD_QUEUE = process.env.STUDIO_BUILD_QUEUE
const runAction = BUILD_QUEUE ? TriggerAction.Enqueue({ queue: BUILD_QUEUE }) : TriggerAction.Void()

// HA: when running >1 replica, only the leader runs the singleton sweep cron.
// STUDIO_LEADER_REDIS=redis://... enables redis-based leader election; otherwise
// this replica is always the leader (single-replica deployments).
const REPLICA_ID = `${process.pid}-${Math.random().toString(36).slice(2, 8)}`
const leader = process.env.STUDIO_LEADER_REDIS
  ? new LeaderLock(new RedisCliLockBackend(process.env.STUDIO_LEADER_REDIS), 'studio:leader:sweep', REPLICA_ID)
  : undefined

// Auth guard for HTTP routes. No-op unless STUDIO_API_TOKEN is set.
function denied(input: unknown): ReturnType<typeof unauthorizedResponse> | null {
  const headers = (input as { headers?: Record<string, string | string[]> }).headers ?? {}
  return checkAuth(headers) ? null : unauthorizedResponse()
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

// --- dashboard UI ---
iii.registerFunction('studio::ui', async () => ({
  status_code: 200,
  headers: { 'content-type': 'text/html; charset=utf-8' },
  body: DASHBOARD_HTML,
}))
iii.registerTrigger({ type: 'http', function_id: 'studio::ui', config: { api_path: '/', http_method: 'GET' } })
iii.registerTrigger({ type: 'http', function_id: 'studio::ui', config: { api_path: '/ui', http_method: 'GET' } })

// --- HTTP intake: POST /projects { idea } -> 202 { project_id } ---
iii.registerFunction('studio::intake::create', async (input) => {
  const d = denied(input)
  if (d) return d
  const body =
    (
      input as {
        body?: {
          idea?: string
          project_id?: string
          idempotency_key?: string
          require_approval?: boolean
        }
      }
    ).body ?? {}
  if (!body.idea) return { status_code: 400, body: { error: 'idea is required' } }

  // Minimal idempotency: a provided, existing project_id returns as-is.
  if (body.project_id) {
    const existing = await deps.store.get(body.project_id)
    if (existing) return { status_code: 200, body: { project_id: existing.project_id } }
  }

  // Deterministic id when an idempotency key is supplied, so a duplicate
  // submission maps to the same project instead of creating a new one.
  const project_id =
    body.project_id ?? (body.idempotency_key ? projectIdFromKey(body.idempotency_key) : randomProjectId())
  const dup = await deps.store.get(project_id)
  if (dup) return { status_code: 200, body: { project_id } }
  await ensureWorkspace(project_id)
  const requireApproval = body.require_approval ?? process.env.STUDIO_REQUIRE_APPROVAL === 'true'
  await deps.store.set({
    ...initialProjectState(project_id, body.idea, workspaceDir(project_id), DEFAULT_MAX_ITERATIONS),
    require_approval: requireApproval,
  })
  // Fire-and-forget: return immediately, run the pipeline in the background.
  iii.trigger({ function_id: 'studio::orch::run', payload: { project_id }, action: runAction })
  return { status_code: 202, body: { project_id } }
})

iii.registerTrigger({
  type: 'http',
  function_id: 'studio::intake::create',
  config: { api_path: '/projects', http_method: 'POST' },
})

// --- DX: inspect projects ---
iii.registerFunction('studio::project::get', async (input) => {
  const d = denied(input)
  if (d) return d
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

// --- approval gate: approve/reject a project waiting for sign-off ---
async function decide(projectId: string, type: 'approved' | 'rejected') {
  const s = await deps.store.get(projectId)
  if (!s) return { status_code: 404, body: { error: 'not found' } }
  if (s.status !== 'awaiting_approval') {
    return { status_code: 409, body: { error: `not awaiting approval (status: ${s.status})` } }
  }
  await advance(deps, projectId, { type })
  const after = await deps.store.get(projectId)
  return { status_code: 200, body: { project_id: projectId, status: after?.status } }
}
iii.registerFunction('studio::project::approve', async (input) => {
  const d = denied(input)
  if (d) return d
  const id = (input as { path_params?: { id?: string } }).path_params?.id
  return id ? decide(id, 'approved') : { status_code: 400, body: { error: 'id required' } }
})
iii.registerTrigger({
  type: 'http',
  function_id: 'studio::project::approve',
  config: { api_path: '/projects/:id/approve', http_method: 'POST' },
})
iii.registerFunction('studio::project::reject', async (input) => {
  const d = denied(input)
  if (d) return d
  const id = (input as { path_params?: { id?: string } }).path_params?.id
  return id ? decide(id, 'rejected') : { status_code: 400, body: { error: 'id required' } }
})
iii.registerTrigger({
  type: 'http',
  function_id: 'studio::project::reject',
  config: { api_path: '/projects/:id/reject', http_method: 'POST' },
})

iii.registerFunction('studio::project::list', async (input) => {
  const d = denied(input)
  if (d) return d
  const all = await deps.store.list()
  const summary = all
    .map((s) => ({
      project_id: s.project_id,
      status: s.status,
      iteration: s.iteration,
      goal: s.spec?.goal,
      app_type: s.plan?.app_type,
      passed: s.last_qa?.passed,
      cost_usd: s.usage?.cost_usd,
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

// --- LLM wiki: auto-generated per-app docs + natural-language Q&A ---
iii.registerFunction('studio::wiki::list', async (input) => {
  const d = denied(input)
  if (d) return d
  const pages = await wiki.list()
  return {
    status_code: 200,
    body: {
      pages: pages
        .map((p) => ({ slug: p.slug, title: p.title, source_project_id: p.source_project_id, updated_at: p.updated_at }))
        .sort((a, b) => (a.updated_at < b.updated_at ? 1 : -1)),
    },
  }
})
iii.registerTrigger({
  type: 'http',
  function_id: 'studio::wiki::list',
  config: { api_path: '/wiki', http_method: 'GET' },
})

iii.registerFunction('studio::wiki::get', async (input) => {
  const d = denied(input)
  if (d) return d
  const slug = (input as { path_params?: { slug?: string } }).path_params?.slug
  if (!slug) return { status_code: 400, body: { error: 'slug required' } }
  const page = await wiki.get(slug)
  return page ? { status_code: 200, body: page } : { status_code: 404, body: { error: 'not found' } }
})
iii.registerTrigger({
  type: 'http',
  function_id: 'studio::wiki::get',
  config: { api_path: '/wiki/:slug', http_method: 'GET' },
})

iii.registerFunction('studio::wiki::ask', async (input) => {
  const d = denied(input)
  if (d) return d
  const question = (input as { body?: { question?: string } }).body?.question
  if (!question) return { status_code: 400, body: { error: 'question is required' } }
  const res = await askWiki(brain, wiki, question)
  return { status_code: 200, body: res }
})
iii.registerTrigger({
  type: 'http',
  function_id: 'studio::wiki::ask',
  config: { api_path: '/wiki/ask', http_method: 'POST' },
})

// --- observability: operational alerts derived from project state ---
iii.registerFunction('studio::alerts', async (input) => {
  const d = denied(input)
  if (d) return d
  const all = await deps.store.list()
  const alerts = detectAlerts(
    all.map((s) => ({ project_id: s.project_id, status: s.status, updated_at: s.updated_at })),
    { stuckMs: Number(process.env.STUDIO_STUCK_MS ?? 10 * 60_000) },
  )
  return { status_code: 200, body: alerts }
})
iii.registerTrigger({
  type: 'http',
  function_id: 'studio::alerts',
  config: { api_path: '/alerts', http_method: 'GET' },
})

// --- crash recovery: periodically resume stuck, non-terminal projects ---
// HA-safe: only the elected leader sweeps, so N replicas don't double-resume.
iii.registerFunction('studio::orch::sweep', async () => {
  if (leader && !(await leader.tryBecomeLeader())) return { skipped: 'not leader' }
  const resumed = await sweep(deps, { stuckMs: Number(process.env.STUDIO_STUCK_MS ?? 5 * 60_000) })
  if (resumed.length) console.log(`[sweep] resumed: ${resumed.join(', ')}`)
  return { resumed }
})
iii.registerTrigger({
  type: 'cron',
  function_id: 'studio::orch::sweep',
  // top of every minute (sec min hour dom mon dow year)
  config: { expression: '0 * * * * * *' },
})

// eslint-disable-next-line no-console
console.log('app-studio worker registered (sandbox::*, studio::intake::create, studio::orch::run)')
