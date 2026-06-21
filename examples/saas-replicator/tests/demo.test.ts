import assert from 'node:assert/strict'
import { test } from 'node:test'
import { runDemo } from '../src/demo'
import { totalTokens } from '../src/logic/budget'

test('runDemo completes end-to-end in stub mode with telemetry (no API keys)', async () => {
  const { project, telemetry } = await runDemo()

  // Pipeline reached the end with every artifact populated.
  assert.equal(project.status, 'done')
  for (const key of ['prd', 'architecture', 'implementation', 'tests', 'visuals', 'deployment'] as const) {
    assert.ok(project.artifacts[key], `${key} present`)
  }

  // Supervisor recorded review rounds for the PRD.
  const reviews = project.artifacts.reviews as Record<string, { rounds: number } | undefined>
  assert.ok((reviews.prd?.rounds ?? 0) >= 1)

  // Claude-only -> the architecture decision used self-critique.
  const arch = project.artifacts.architecture as { mode: string; answer: string }
  assert.equal(arch.mode, 'self-critique')
  assert.ok(arch.answer.length > 0)

  // Observability captured spans and metered provider token usage.
  assert.ok(telemetry.spans.length > 0, 'spans recorded')
  assert.ok(telemetry.budget.calls > 0, 'provider calls metered')
  assert.ok(totalTokens(telemetry.budget) >= 0)
})
