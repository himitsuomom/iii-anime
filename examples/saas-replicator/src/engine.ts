/**
 * Engine abstraction the orchestrator handlers run against.
 *
 * Two adapters implement it:
 *  - `iiiEngine` (src/adapters/iiiEngine.ts) — the real iii bus.
 *  - `MemoryEngine` (src/adapters/memoryEngine.ts) — in-memory, for tests.
 *
 * Handlers only ever use `call` / `enqueue` / `register` / `listWorkers`, so the
 * exact same orchestration code runs in production and in unit tests.
 */

// biome-ignore lint/suspicious/noExplicitAny: handler payloads are arbitrary JSON
export type Json = any

export type Handler = (payload: Json) => Promise<Json>

export interface HttpBinding {
  path: string
  method: string
  description?: string
}

export interface RegisterOptions {
  description?: string
  /** When set, the real adapter also exposes the function over HTTP. */
  http?: HttpBinding
  metadata?: Record<string, unknown>
}

export interface WorkerInfo {
  name: string
}

export interface Engine {
  /** Register a function by id (and optionally an HTTP trigger). */
  register(functionId: string, handler: Handler, opts?: RegisterOptions): void
  /** Synchronous request/response invocation of a function. */
  call<T = Json>(functionId: string, payload?: Json): Promise<T>
  /** Enqueue onto a named queue (async fan-out / handoff). */
  enqueue(functionId: string, payload: Json, queue: string): Promise<{ messageReceiptId: string }>
  /** List connected workers (used to detect optional providers like KIMI). */
  listWorkers(): Promise<WorkerInfo[]>
}
