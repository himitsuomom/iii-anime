import { registerWorker } from 'iii-sdk'

const engineWsUrl = process.env.III_URL ?? 'ws://localhost:49134'

export const iii = registerWorker(engineWsUrl, {
  workerName: 'freellmapi-worker',
  workerDescription:
    'Aggregates free-tier LLM providers (Google Gemini, Groq, Cerebras, Mistral, Pollinations) behind an OpenAI-compatible endpoint',
  otel: {
    enabled: process.env.OTEL_ENABLED !== 'false',
    serviceName: 'freellmapi-worker',
  },
})
