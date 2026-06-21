// Idempotency helpers. A deterministic project id derived from an idempotency
// key means a duplicate submission maps to the same project (and the create
// handler can short-circuit to the existing one). See IDEMPOTENCY-RESUME.md §1.
import { createHash } from 'node:crypto'

/** Stable project id for a given idempotency key (same key -> same id). */
export function projectIdFromKey(key: string): string {
  const h = createHash('sha256').update(key).digest('hex').slice(0, 16)
  return `prj_${h}`
}

/** A fresh, non-deterministic project id (used when no idempotency key is given). */
export function randomProjectId(): string {
  return `prj_${Date.now().toString(36)}${Math.random().toString(36).slice(2, 8)}`
}
