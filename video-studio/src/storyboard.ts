import type { Shot, Storyboard } from './types.js'

/** Validate an LLM-produced storyboard (the video analog of app-studio's Plan). */
export function validateStoryboard(u: unknown): Storyboard {
  const o = asObject(u, 'storyboard')
  const shots = arr(o.shots, 'shots').map((s, i) => validateShot(s, i))
  if (shots.length === 0) throw new Error('storyboard must have at least one shot')
  const sb: Storyboard = {
    title: str(o.title, 'title'),
    shots,
    output: str(o.output, 'output'),
  }
  if (o.audio !== undefined) sb.audio = str(o.audio, 'audio')
  return sb
}

function validateShot(u: unknown, i: number): Shot {
  const o = asObject(u, `shots[${i}]`)
  const seconds = num(o.seconds, `shots[${i}].seconds`)
  if (seconds <= 0) throw new Error(`shots[${i}].seconds must be > 0`)
  const shot: Shot = { image: str(o.image, `shots[${i}].image`), seconds }
  if (o.caption !== undefined) shot.caption = str(o.caption, `shots[${i}].caption`)
  return shot
}

function asObject(u: unknown, what: string): Record<string, unknown> {
  if (typeof u !== 'object' || u === null || Array.isArray(u)) throw new Error(`${what}: expected object`)
  return u as Record<string, unknown>
}
function arr(v: unknown, f: string): unknown[] {
  if (!Array.isArray(v)) throw new Error(`${f}: expected array`)
  return v
}
function str(v: unknown, f: string): string {
  if (typeof v !== 'string' || !v) throw new Error(`${f}: expected non-empty string`)
  return v
}
function num(v: unknown, f: string): number {
  if (typeof v !== 'number' || !Number.isFinite(v)) throw new Error(`${f}: expected number`)
  return v
}
