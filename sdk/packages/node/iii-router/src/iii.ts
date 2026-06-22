import { registerWorker } from 'iii-sdk'
import { version } from '../package.json'

// Engine WebSocket URL — used for both iii and telemetry.
// biome-ignore lint/suspicious/noExplicitAny: process.env is not typed in this context
const engineWsUrl = (process.env as any).III_URL ?? 'ws://localhost:49134'

export const iii = registerWorker(engineWsUrl, {
  otel: {
    enabled: true,
    serviceName: 'iii-router',
    metricsEnabled: true,
    serviceVersion: version,
    reconnectionConfig: {
      maxRetries: 10,
    },
    metricsExportIntervalMs: 10000,
  },
})
