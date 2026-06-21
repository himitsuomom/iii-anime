import { EngineFunctions, registerWorker, TriggerAction } from 'iii-sdk'
import type { Engine, Handler, Json, RegisterOptions, WorkerInfo } from '../engine'

/**
 * Real adapter: binds the Engine interface to the iii bus. Function calls and
 * enqueues become `iii.trigger` invocations; `register` wires up functions and
 * (optionally) HTTP triggers.
 */
export function createIIIEngine(url = process.env.III_URL ?? 'ws://localhost:49134'): Engine {
  const iii = registerWorker(url, {
    workerName: 'saas-replicator',
    otel: {
      enabled: true,
      serviceName: 'saas-replicator',
      metricsEnabled: true,
      reconnectionConfig: { maxRetries: 10 },
    },
  })

  return {
    register(functionId: string, handler: Handler, opts?: RegisterOptions) {
      iii.registerFunction(functionId, (payload) => handler(payload), {
        description: opts?.description,
        metadata: opts?.metadata,
      })
      if (opts?.http) {
        iii.registerTrigger({
          type: 'http',
          function_id: functionId,
          config: { api_path: opts.http.path, http_method: opts.http.method, description: opts.http.description },
        })
      }
    },
    call<T = Json>(functionId: string, payload?: Json): Promise<T> {
      return iii.trigger<Json, T>({ function_id: functionId, payload })
    },
    async enqueue(functionId: string, payload: Json, queue: string) {
      return iii.trigger<Json, { messageReceiptId: string }>({
        function_id: functionId,
        payload,
        action: TriggerAction.Enqueue({ queue }),
      })
    },
    async listWorkers(): Promise<WorkerInfo[]> {
      const workers = await iii.trigger<unknown, Array<{ name?: string; worker_name?: string }>>({
        function_id: EngineFunctions.LIST_WORKERS,
        payload: {},
      })
      if (!Array.isArray(workers)) return []
      return workers.map((w) => ({ name: w?.name ?? w?.worker_name ?? '' }))
    },
  }
}
