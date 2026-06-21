import assert from 'node:assert/strict'
import { test } from 'node:test'
import { MemoryEngine } from '../src/adapters/memoryEngine'
import {
  addUsage,
  BudgetExceededError,
  emptyBudget,
  extractUsage,
  isProviderCall,
  overBudget,
  totalTokens,
} from '../src/logic/budget'
import { STUB_FUNCTION_ID } from '../src/logic/roleBinding'
import { withObservability } from '../src/observability'

test('budget pure helpers: extract, add, over, classify', () => {
  assert.deepEqual(extractUsage({ usage: { input_tokens: 10, output_tokens: 5 } }), { input: 10, output: 5 })
  assert.deepEqual(extractUsage({}), { input: 0, output: 0 })

  const b = addUsage(addUsage(emptyBudget(), { input: 10, output: 5 }), { input: 1, output: 2 })
  assert.equal(totalTokens(b), 18)
  assert.equal(b.calls, 2)

  assert.equal(overBudget(b, 0), false) // 0 = unlimited
  assert.equal(overBudget(b, 100), false)
  assert.equal(overBudget(b, 18), true)

  assert.equal(isProviderCall('provider-anthropic::messages'), true)
  assert.equal(isProviderCall('provider-kimi::messages'), true)
  assert.equal(isProviderCall(STUB_FUNCTION_ID), true)
  assert.equal(isProviderCall('state::get'), false)
  assert.equal(isProviderCall('director::advance'), false)
})

test('decorator meters provider calls only, not state ops', async () => {
  const inner = new MemoryEngine()
  inner.register(STUB_FUNCTION_ID, async () => ({ content: 'x', usage: { input_tokens: 7, output_tokens: 3 } }))
  const engine = withObservability(inner)

  await engine.call('state::set', { scope: 's', key: 'k', value: 1 })
  await engine.call('state::get', { scope: 's', key: 'k' })
  assert.equal(engine.telemetry.budget.calls, 0) // state ops not metered
  assert.ok(engine.telemetry.spans.length >= 2) // but still traced

  await engine.call(STUB_FUNCTION_ID, { messages: [] })
  assert.equal(engine.telemetry.budget.calls, 1)
  assert.equal(totalTokens(engine.telemetry.budget), 10)
})

test('decorator throws BudgetExceededError once the ceiling is reached', async () => {
  const inner = new MemoryEngine()
  inner.register(STUB_FUNCTION_ID, async () => ({ content: 'x', usage: { input_tokens: 6, output_tokens: 0 } }))
  const engine = withObservability(inner, { budgetTokens: 5 })

  // Pre-call check: first call sees 0 used (under 5) and proceeds, spending 6.
  await engine.call(STUB_FUNCTION_ID, { messages: [] })
  // Second call sees 6 used (>= 5) and is rejected before spending more.
  await assert.rejects(
    () => engine.call(STUB_FUNCTION_ID, { messages: [] }),
    (err) => err instanceof BudgetExceededError,
  )
})
