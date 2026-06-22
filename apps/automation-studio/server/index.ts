import { serve } from '@hono/node-server'
import { serveStatic } from '@hono/node-server/serve-static'
import { Hono } from 'hono'
import { hasApiKey } from './anthropic.ts'
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
