import { serve } from '@hono/node-server'
import { serveStatic } from '@hono/node-server/serve-static'
import { Hono } from 'hono'
import { hasApiKey, MODEL } from './anthropic.ts'
import { startAiWorker } from './iii-worker.ts'
import { getMetrics } from './lib/metrics.ts'
import { chatRoute } from './routes/chat.ts'
import { generateRoute } from './routes/generate.ts'

// Load environment variables from a local .env file when present (Node ≥ 21.7).
try {
  process.loadEnvFile?.()
} catch {
  // No .env file — rely on the ambient environment.
}

const app = new Hono()

const api = new Hono()
api.get('/health', (c) => c.json({ ok: true, hasApiKey: hasApiKey() }))
// Live runtime metrics for the dashboard (real counts this instance has done).
api.get('/stats', (c) =>
  c.json({
    ...getMetrics(),
    hasApiKey: hasApiKey(),
    model: MODEL,
    workerConnected: Boolean(process.env.III_URL),
  }),
)
api.route('/generate-description', generateRoute)
api.route('/chat', chatRoute)

app.route('/api', api)

// Serve the built frontend in production. In development the Vite dev server
// handles the UI and proxies /api here, so these routes simply 404 (harmless).
app.use('/*', serveStatic({ root: './dist' }))
app.get('/*', serveStatic({ path: './dist/index.html' }))

const port = Number(process.env.PORT) || 8787
serve({ fetch: app.fetch, port }, (info) => {
  console.log(`automation-studio api listening on http://localhost:${info.port}`)
  if (!hasApiKey()) {
    console.warn('  ⚠  ANTHROPIC_API_KEY is not set — running in offline mode (template / FAQ fallbacks).')
  }
})

// When III_URL is set, also join the iii engine as a worker and expose the AI
// functions (ai::describe-product / ai::answer-inquiry). HTTP-only runs (no
// III_URL) skip this entirely.
startAiWorker(process.env.III_URL)
  .then((worker) => {
    if (worker) console.log(`automation-studio worker registered on ${process.env.III_URL}`)
  })
  .catch((err) => {
    console.error('failed to start iii worker:', err)
  })
