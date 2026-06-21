/**
 * Pure token-budget accounting (no iii-sdk imports — unit-testable).
 *
 * Realizes the "cost blow-up / SPOF" mitigation from DESIGN §12: every provider
 * call's token usage is accumulated and checked against a ceiling. Mirrors the
 * `llm-budget` harness worker, but runs in-process so the example enforces a
 * cap even with only `provider-anthropic` (or the stub) available.
 */

import { providerFunctionId } from './roleBinding'

export interface Usage {
  input: number
  output: number
}

export interface BudgetState {
  inputTokens: number
  outputTokens: number
  /** Number of provider calls counted. */
  calls: number
}

/** Raised by the observability decorator when a call would exceed the ceiling. */
export class BudgetExceededError extends Error {
  constructor(
    readonly used: number,
    readonly limit: number,
  ) {
    super(`token budget exceeded: ${used} >= ${limit}`)
    this.name = 'BudgetExceededError'
  }
}

export function emptyBudget(): BudgetState {
  return { inputTokens: 0, outputTokens: 0, calls: 0 }
}

/** Total tokens consumed so far (input + output). */
export function totalTokens(state: BudgetState): number {
  return state.inputTokens + state.outputTokens
}

/** Read `{ usage: { input_tokens, output_tokens } }` from a provider response. */
export function extractUsage(response: unknown): Usage {
  const usage =
    response && typeof response === 'object' ? ((response as { usage?: Record<string, unknown> }).usage ?? {}) : {}
  return {
    input: num(usage.input_tokens),
    output: num(usage.output_tokens),
  }
}

/** Fold a usage record into the running budget (returns a new state). */
export function addUsage(state: BudgetState, usage: Usage): BudgetState {
  return {
    inputTokens: state.inputTokens + usage.input,
    outputTokens: state.outputTokens + usage.output,
    calls: state.calls + 1,
  }
}

/** True when consumption has reached/passed the limit (limit <= 0 means no cap). */
export function overBudget(state: BudgetState, limit: number): boolean {
  if (!limit || limit <= 0) return false
  return totalTokens(state) >= limit
}

/** True when `functionId` is a model/provider invocation that should be metered. */
export function isProviderCall(functionId: string): boolean {
  return (
    functionId === providerFunctionId('anthropic') ||
    functionId === providerFunctionId('kimi') ||
    functionId === providerFunctionId('stub')
  )
}

function num(v: unknown): number {
  const n = typeof v === 'number' ? v : Number(v)
  return Number.isFinite(n) ? n : 0
}
