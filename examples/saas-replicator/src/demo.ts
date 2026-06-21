/**
 * End-to-end stub demo (no API keys, no live engine).
 *
 * Proves the whole 4-phase pipeline runs to `done` on Claude-only / stub mode:
 * builds an in-memory engine wrapped with observability + budget, registers the
 * orchestrator, starts a Trello run with 3 screenshots, drains the queue, and
 * prints the artifacts, span count, and token usage. Run: `npm run demo`.
 */

import { MemoryEngine } from './adapters/memoryEngine'
import { startProject } from './director'
import { totalTokens } from './logic/budget'
import type { ProjectState } from './logic/pipeline'
import { type ObservableEngine, withObservability } from './observability'
import { registerOrchestrator } from './orchestrator'

export interface DemoResult {
  project: ProjectState
  telemetry: ObservableEngine['telemetry']
}

/** Run the full pipeline in stub mode and return the final state + telemetry. */
export async function runDemo(): Promise<DemoResult> {
  process.env.SAAS_PROVIDER_MODE = 'stub'

  const inner = new MemoryEngine()
  const engine = withObservability(inner)
  registerOrchestrator(engine)

  const { projectId } = await startProject(engine, {
    target: 'Trello',
    requirements: 'JP UI / PWA / responsive',
    screenshots: [{ id: 'board' }, { id: 'card' }, { id: 'modal' }],
  })

  // Handlers close over the observable `engine`, so provider calls during the
  // drain are still traced/metered; the queue itself lives on the inner engine.
  await inner.drain()
  const project = await engine.call<ProjectState>('state::get', { scope: `saas/${projectId}`, key: 'project' })
  return { project, telemetry: engine.telemetry }
}

/** Pretty-print a demo result to the console. */
export function reportDemo({ project, telemetry }: DemoResult): void {
  const a = project.artifacts
  console.log('\n=== SaaS Replicator demo (stub mode, no API keys) ===')
  console.log(`status:        ${project.status}`)
  console.log(`target:        ${project.target}`)
  console.log(`artifacts:     ${Object.keys(a).join(', ')}`)
  console.log(
    `architecture:  ${(a.architecture as { mode?: string; answer?: string })?.mode} -> ${(a.architecture as { answer?: string })?.answer}`,
  )
  console.log(`tests:         ${JSON.stringify(a.tests)}`)
  console.log(`spans:         ${telemetry.spans.length}`)
  console.log(
    `tokens:        ${totalTokens(telemetry.budget)} over ${telemetry.budget.calls} provider calls (limit ${telemetry.budgetLimit || 'unlimited'})`,
  )
}

// Execute when run directly (tsx src/demo.ts), not when imported by tests.
if (import.meta.url === `file://${process.argv[1]}`) {
  runDemo()
    .then((result) => {
      reportDemo(result)
      if (result.project.status !== 'done') {
        console.error('demo did not reach done')
        process.exit(1)
      }
      process.exit(0)
    })
    .catch((err) => {
      console.error('demo failed:', err)
      process.exit(1)
    })
}
