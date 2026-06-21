// HTTP auth gate for factory routes. Disabled by default (open, for dev/tests);
// when STUDIO_API_TOKEN is set, sensitive routes require a matching bearer token
// (Authorization: Bearer <token>) or x-api-key header. Production: front the
// engine with a real auth gateway; this is a baseline guard, not a full IdP.
import { timingSafeEqual } from 'node:crypto'

export type Headers = Record<string, string | string[] | undefined>

export function authToken(env: NodeJS.ProcessEnv = process.env): string | undefined {
  return env.STUDIO_API_TOKEN || undefined
}

export function authEnabled(env: NodeJS.ProcessEnv = process.env): boolean {
  return !!authToken(env)
}

/** True if the request is authorized (or auth is disabled). */
export function checkAuth(headers: Headers, env: NodeJS.ProcessEnv = process.env): boolean {
  const token = authToken(env)
  if (!token) return true // auth disabled
  const provided = bearer(headers['authorization'] ?? headers['Authorization']) ?? one(headers['x-api-key'] ?? headers['X-Api-Key'])
  return !!provided && safeEqual(provided, token)
}

export function unauthorizedResponse() {
  return {
    status_code: 401,
    headers: { 'content-type': 'application/json' },
    body: { error: 'unauthorized' },
  }
}

function one(v: string | string[] | undefined): string | undefined {
  return Array.isArray(v) ? v[0] : v
}
function bearer(v: string | string[] | undefined): string | undefined {
  const s = one(v)
  if (!s) return undefined
  const m = /^Bearer\s+(.+)$/i.exec(s.trim())
  return m ? m[1] : undefined
}
function safeEqual(a: string, b: string): boolean {
  const ab = Buffer.from(a)
  const bb = Buffer.from(b)
  if (ab.length !== bb.length) return false
  return timingSafeEqual(ab, bb)
}
