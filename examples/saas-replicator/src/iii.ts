import { registerWorker } from 'iii-sdk'

const engineWsUrl = process.env.III_URL ?? 'ws://localhost:49134'

/** Shared worker connection for the SaaS Replicator orchestrator. */
export const iii = registerWorker(engineWsUrl, {
  workerName: 'saas-replicator',
  otel: {
    enabled: true,
    serviceName: 'saas-replicator',
    metricsEnabled: true,
    reconnectionConfig: { maxRetries: 10 },
  },
})
