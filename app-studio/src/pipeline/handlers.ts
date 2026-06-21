// Pipeline handlers — one per pipeline stage. Each does its work, persists the
// result to the store, and returns the completion event that the orchestrator
// feeds back into the state machine. Backend-agnostic: the build "brain" and
// build backend are injected (see BUILD-BACKENDS.md).
import { designGuidanceBlock, rubricFor } from '../adapters/registry.js'
import type { BuildBackend } from '../build/backend.js'
import type { Brain } from '../brain/brain.js'
import { validatePlan, validateSpec } from '../brain/brain.js'
import { execInWorkspace } from '../sandbox/exec.js'
import { ensureWorkspace, listWorkspaceFiles } from '../sandbox/workspace.js'
import type { Store } from '../runtime/store.js'
import type { WikiStore } from '../wiki/wiki-store.js'
import { generateWikiPage } from '../wiki/wiki.js'
import { renderWikiContext, selectRelevantPages } from '../wiki/retrieval.js'
import type { PipelineEvent, Plan, ProjectState, QaResult, Spec } from '../types.js'

export interface StudioDeps {
  store: Store
  brain: Brain
  build: BuildBackend
  /** Optional wiki: when set, deliver auto-documents the app into it. */
  wiki?: WikiStore
  /** Hard cap on build-agent turns per attempt. */
  buildMaxTurns?: number
}

export type FunctionId =
  | 'studio::intake::spec'
  | 'studio::design::plan'
  | 'studio::build::run'
  | 'studio::qa::evaluate'
  | 'studio::deliver::package'

export function handlerFor(
  deps: StudioDeps,
  fn: FunctionId,
): (projectId: string) => Promise<PipelineEvent> {
  switch (fn) {
    case 'studio::intake::spec':
      return (id) => intakeSpec(deps, id)
    case 'studio::design::plan':
      return (id) => designPlan(deps, id)
    case 'studio::build::run':
      return (id) => buildRun(deps, id)
    case 'studio::qa::evaluate':
      return (id) => qaEvaluate(deps, id)
    case 'studio::deliver::package':
      return (id) => deliverPackage(deps, id)
  }
}

const INTAKE_SYSTEM =
  'You turn a rough product idea into a precise, buildable specification for a small web ' +
  'application. Do not ask questions; choose sensible minimal defaults and record each in ' +
  '"assumptions". "acceptance" must be concrete and checkable. Keep scope minimal. ' +
  'P0 constraint: the app must be implementable with ZERO external dependencies (Node.js ' +
  'standard library only — no npm installs). ' +
  'Shape: {goal:string, features:string[], acceptance:string[], constraints?:string[], assumptions:string[]}.'

const DESIGN_SYSTEM =
  'You are a software architect. Given a specification, produce a minimal implementation plan. ' +
  'Choose the single best app_type from the catalog below and follow ITS guidance exactly — ' +
  'build_cmd and test_cmd are what QA runs to decide pass/fail. Do not over-engineer.\n\n' +
  'App types:\n' +
  designGuidanceBlock() +
  '\n\nShape: {app_type:string (one of the ids above), stack:string[], tasks:string[], ' +
  'build_cmd:string, test_cmd:string, run_cmd?:string}.'

// Condensed from prompts/BUILD_SYSTEM_PROMPT.md (kept in sync there).
const BUILD_SYSTEM =
  'You are a senior engineer working autonomously in a sandboxed workspace (the current ' +
  'directory). Implement the app from the spec and plan using ONLY the Node.js standard library ' +
  '(e.g. node:http, node:test) — no npm install, no external packages. Definition of done: the ' +
  'build command exits 0, the test command exits 0, and every acceptance criterion holds — run ' +
  'these yourself and read the output before claiming done. Write tests as *.test.js using ' +
  "node:test and node:assert. Work test-driven. Make small targeted edits. Build the simplest " +
  'thing that satisfies the spec; do not add unrequested features or abstractions. Default to ' +
  'silence between tool calls. End only when `node --test` passes.'

async function intakeSpec(deps: StudioDeps, projectId: string): Promise<PipelineEvent> {
  const s = await must(deps.store, projectId)
  const spec = await deps.brain.json<Spec>({
    system: INTAKE_SYSTEM,
    user: `Idea:\n${s.idea}\n\nProduce the specification.`,
    validate: validateSpec,
  })
  await deps.store.update(projectId, { spec })
  return { type: 'spec.ready' }
}

async function designPlan(deps: StudioDeps, projectId: string): Promise<PipelineEvent> {
  const s = await must(deps.store, projectId)
  const plan = await deps.brain.json<Plan>({
    system: DESIGN_SYSTEM,
    user: `Specification:\n${JSON.stringify(s.spec, null, 2)}\n\nProduce the plan.`,
    validate: validatePlan,
  })
  await deps.store.update(projectId, { plan })
  return { type: 'plan.ready' }
}

async function buildRun(deps: StudioDeps, projectId: string): Promise<PipelineEvent> {
  const s = await must(deps.store, projectId)
  await ensureWorkspace(projectId)
  const feedback = s.last_qa?.failures?.length ? s.last_qa.failures.join('\n') : undefined
  const priorWork = await relevantPriorWork(deps, projectId, s)
  const out = await deps.build.run({
    project_id: projectId,
    workdir: s.workdir,
    systemPrompt: BUILD_SYSTEM,
    userPrompt: renderBuildPrompt(s, feedback, priorWork),
    maxTurns: deps.buildMaxTurns ?? 60,
  })
  const files = await listWorkspaceFiles(projectId)
  await deps.store.update(projectId, {
    artifacts: { ...(s.artifacts ?? {}), files },
  })
  // The backend completing isn't a guarantee tests pass — QA decides that next.
  if (!out.ok) {
    // Record the backend error so QA/feedback can see it, but still let QA run.
    await deps.store.update(projectId, {
      last_qa: { passed: false, failures: [out.error ?? 'build backend error'], score: 0 },
    })
  }
  return { type: 'build.done' }
}

async function qaEvaluate(deps: StudioDeps, projectId: string): Promise<PipelineEvent> {
  const s = await must(deps.store, projectId)
  const rubric = rubricFor(s.plan)
  const failures: string[] = []
  for (const check of rubric.hard) {
    const r = await execInWorkspace({ project_id: projectId, cmd: check.cmd })
    if (r.exit_code !== 0 || r.timed_out) {
      failures.push(`[${check.id}] \`${check.cmd}\` exited ${r.exit_code}${r.timed_out ? ' (timeout)' : ''}: ${tail(r.stderr || r.stdout)}`)
    }
  }
  const result: QaResult = {
    passed: failures.length === 0,
    failures,
    score: failures.length === 0 ? 100 : 0,
  }
  await deps.store.update(projectId, { last_qa: result })
  return { type: result.passed ? 'qa.passed' : 'qa.failed' }
}

async function deliverPackage(deps: StudioDeps, projectId: string): Promise<PipelineEvent> {
  const s = await must(deps.store, projectId)
  const files = await listWorkspaceFiles(projectId)
  const updated = await deps.store.update(projectId, {
    artifacts: { ...(s.artifacts ?? {}), files, preview_cmd: s.plan?.run_cmd },
  })
  // Wiki link-up: auto-document the delivered app. Best-effort — never fail
  // delivery because the wiki page couldn't be written.
  if (deps.wiki) {
    try {
      const page = await generateWikiPage(deps.brain, updated)
      await deps.wiki.put(page)
    } catch {
      /* wiki is best-effort */
    }
  }
  return { type: 'delivered' }
}

/** Pull relevant prior app docs from the wiki to seed the build (best-effort). */
async function relevantPriorWork(
  deps: StudioDeps,
  projectId: string,
  s: ProjectState,
): Promise<string> {
  if (!deps.wiki) return ''
  try {
    const pages = (await deps.wiki.list()).filter((p) => p.source_project_id !== projectId)
    const query = `${s.spec?.goal ?? s.idea} ${(s.spec?.features ?? []).join(' ')}`
    return renderWikiContext(selectRelevantPages(pages, query, 3))
  } catch {
    return ''
  }
}

function renderBuildPrompt(s: ProjectState, feedback?: string, priorWork?: string): string {
  const spec = JSON.stringify(s.spec, null, 2)
  const plan = JSON.stringify(s.plan, null, 2)
  const head = feedback
    ? `The previous attempt did not pass QA. Fix these failures:\n${feedback}\n\n`
    : ''
  const prior = priorWork ? `${priorWork}\n\n` : ''
  return (
    `${head}${prior}Implement the application in the current directory.\n\n` +
    `## Specification\n${spec}\n\n## Plan\n${plan}\n\n` +
    `Make \`${s.plan?.test_cmd ?? 'the tests'}\` pass.`
  )
}

async function must(store: Store, projectId: string): Promise<ProjectState> {
  const s = await store.get(projectId)
  if (!s) throw new Error(`unknown project: ${projectId}`)
  return s
}

function tail(s: string, n = 200): string {
  const t = s.trim()
  return t.length > n ? `…${t.slice(-n)}` : t
}
