/**
 * Observability + budget Engine decorator (DESIGN §12).
 *
 * Wraps any {@link Engine} (real iii bus or `MemoryEngine`) and intercepts
 * `call`/`enqueue` to: (1) record a timed span per invocation, and (2) meter
 * token usage of provider calls against a ceiling, throwing
 * `BudgetExceededError` before a call that would exceed it. Handlers are
 * untouched — they keep using the plain `Engine` surface. `register` and
 * `listWorkers` pass straight through.
 *
 * The real adapter already enables OTel at the transport layer
 * (`adapters/iiiEngine.ts`); these spans are app-level and complement it.
 */

import type { Engine, Handler, Json, RegisterOptions, WorkerInfo } from './engine'
import { Logger } from './log'
import {
  addUsage,
  BudgetExceededError,
  type BudgetState,
  emptyBudget,
  extractUsage,
  isProviderCall,
  overBudget,
  totalTokens,
} from './logic/budget'

export interface Span {
  functionId: string
  kind: 'call' | 'enqueue'
  durationMs: number
  ok: boolean
  error?: string
}

export interface Telemetry {
  spans: Span[]
  budget: BudgetState
  /** Token ceiling in effect (0 = unlimited). */
  budgetLimit: number
}

export interface ObservabilityOptions {
  /** Token ceiling. 0/undefined = unlimited. Defaults to `SAAS_TOKEN_BUDGET`. */
  budgetTokens?: number
}

export type ObservableEngine = Engine & { telemetry: Telemetry }

const logger = new Logger(undefined, 'observability')

function envBudget(): number {
  const n = Number(process.env.SAAS_TOKEN_BUDGET)
  return Number.isFinite(n) && n > 0 ? n : 0
}

/** Wrap an engine with span tracing + token-budget enforcement. */
export function withObservability(engine: Engine, opts: ObservabilityOptions = {}): ObservableEngine {
  const budgetLimit = opts.budgetTokens ?? envBudget()
  const telemetry: Telemetry = { spans: [], budget: emptyBudget(), budgetLimit }

  const record = (span: Span) => {
    telemetry.spans.push(span)
    logger.info('span', { fn: span.functionId, kind: span.kind, ms: Math.round(span.durationMs), ok: span.ok })
  }

  return {
    telemetry,

    register(functionId: string, handler: Handler, options?: RegisterOptions) {
      engine.register(functionId, handler, options)
    },

    async call<T = Json>(functionId: string, payload?: Json): Promise<T> {
      // Enforce the ceiling *before* spending more on a provider call.
      if (isProviderCall(functionId) && overBudget(telemetry.budget, budgetLimit)) {
        throw new BudgetExceededError(totalTokens(telemetry.budget), budgetLimit)
      }
      const start = now()
      try {
        const result = await engine.call<T>(functionId, payload)
        if (isProviderCall(functionId)) telemetry.budget = addUsage(telemetry.budget, extractUsage(result))
        record({ functionId, kind: 'call', durationMs: now() - start, ok: true })
        return result
      } catch (err) {
        record({ functionId, kind: 'call', durationMs: now() - start, ok: false, error: String(err) })
        throw err
      }
    },

    async enqueue(functionId: string, payload: Json, queue: string) {
      const start = now()
      try {
        const res = await engine.enqueue(functionId, payload, queue)
        record({ functionId, kind: 'enqueue', durationMs: now() - start, ok: true })
        return res
      } catch (err) {
        record({ functionId, kind: 'enqueue', durationMs: now() - start, ok: false, error: String(err) })
        throw err
      }
    },

    listWorkers(): Promise<WorkerInfo[]> {
      return engine.listWorkers()
    },
  }
}

function now(): number {
  return typeof performance !== 'undefined' ? performance.now() : Date.now()
}
