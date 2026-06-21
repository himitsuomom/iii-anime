import type { Engine, Handler, Json, RegisterOptions, WorkerInfo } from '../engine'

interface QueuedMessage {
  functionId: string
  payload: Json
}

/**
 * In-memory Engine for tests. Provides the same surface as the real iii bus:
 * a function registry, an in-memory `state::*` store, a worker list, and a queue
 * you drain manually. Enqueued messages run through the same handlers, so a full
 * 4-phase run can be exercised without a live engine or any API keys.
 */
export class MemoryEngine implements Engine {
  private readonly fns = new Map<string, Handler>()
  private readonly store = new Map<string, Map<string, Json>>()
  private readonly queue: QueuedMessage[] = []
  private readonly workers: WorkerInfo[]

  constructor(workers: WorkerInfo[] = []) {
    this.workers = workers
  }

  register(functionId: string, handler: Handler, _opts?: RegisterOptions): void {
    this.fns.set(functionId, handler)
  }

  async call<T = Json>(functionId: string, payload?: Json): Promise<T> {
    if (functionId.startsWith('state::')) return this.state(functionId, payload) as T
    if (functionId === 'engine::workers::list') return this.workers as unknown as T
    const fn = this.fns.get(functionId)
    if (!fn) throw new Error(`function not registered: ${functionId}`)
    return (await fn(payload)) as T
  }

  async enqueue(functionId: string, payload: Json, _queue: string): Promise<{ messageReceiptId: string }> {
    this.queue.push({ functionId, payload })
    return { messageReceiptId: `mem-${this.queue.length}` }
  }

  async listWorkers(): Promise<WorkerInfo[]> {
    return this.workers
  }

  /** Process every queued message (and any they enqueue) until the queue drains. */
  async drain(maxIterations = 10_000): Promise<void> {
    let i = 0
    while (this.queue.length > 0) {
      if (i++ > maxIterations) throw new Error('drain exceeded max iterations (possible loop)')
      const msg = this.queue.shift() as QueuedMessage
      await this.call(msg.functionId, msg.payload)
    }
  }

  private scope(scope: string): Map<string, Json> {
    let m = this.store.get(scope)
    if (!m) {
      m = new Map()
      this.store.set(scope, m)
    }
    return m
  }

  private state(functionId: string, payload: Json): Json {
    const op = functionId.slice('state::'.length)
    if (op === 'get') return this.scope(payload.scope).get(payload.key) ?? null
    if (op === 'set') {
      this.scope(payload.scope).set(payload.key, payload.value)
      return payload.value
    }
    if (op === 'list') return [...this.scope(payload.scope).values()]
    if (op === 'delete') {
      this.scope(payload.scope).delete(payload.key)
      return { deleted: true }
    }
    throw new Error(`unsupported state op: ${functionId}`)
  }
}
