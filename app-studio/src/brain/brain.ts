// The "brain" used by intake/design (and optional QA review). Like the build
// backend, it is pluggable: ClaudeCliBrain drives `claude -p` (no API key), a
// future ApiBrain could call the Anthropic SDK. Tests use a fake.
import { adapterIds } from '../adapters/registry.js'
import type { Plan, Spec } from '../types.js'

export interface JsonRequest<T> {
  system: string
  user: string
  /** Validate + narrow the parsed JSON; throw on a bad shape. */
  validate: (parsed: unknown) => T
  maxTurns?: number
}

export interface TextRequest {
  system: string
  user: string
  maxTurns?: number
}

export interface Brain {
  readonly id: string
  json<T>(req: JsonRequest<T>): Promise<T>
  /** Free-text generation (used by the wiki feature). */
  text(req: TextRequest): Promise<string>
}

// --- Runtime validators (hand-rolled; avoids a zod dependency for P0) ---

export function validateSpec(u: unknown): Spec {
  const o = asObject(u, 'spec')
  const spec: Spec = {
    goal: str(o.goal, 'goal'),
    features: strArray(o.features, 'features'),
    acceptance: strArray(o.acceptance, 'acceptance'),
    assumptions: strArray(o.assumptions, 'assumptions'),
  }
  if (o.constraints !== undefined) spec.constraints = strArray(o.constraints, 'constraints')
  return spec
}

export function validatePlan(u: unknown): Plan {
  const o = asObject(u, 'plan')
  const appType = str(o.app_type, 'app_type')
  if (!adapterIds().includes(appType)) {
    throw new Error(`plan.app_type "${appType}" is not a known app type (${adapterIds().join(', ')})`)
  }
  const plan: Plan = {
    app_type: appType,
    stack: strArray(o.stack, 'stack'),
    tasks: strArray(o.tasks, 'tasks'),
    build_cmd: str(o.build_cmd, 'build_cmd'),
    test_cmd: str(o.test_cmd, 'test_cmd'),
  }
  if (o.run_cmd !== undefined) plan.run_cmd = str(o.run_cmd, 'run_cmd')
  return plan
}

function asObject(u: unknown, what: string): Record<string, unknown> {
  if (typeof u !== 'object' || u === null || Array.isArray(u)) {
    throw new Error(`${what}: expected an object`)
  }
  return u as Record<string, unknown>
}
function str(v: unknown, field: string): string {
  if (typeof v !== 'string' || v.length === 0) throw new Error(`${field}: expected non-empty string`)
  return v
}
function strArray(v: unknown, field: string): string[] {
  if (!Array.isArray(v) || !v.every((x) => typeof x === 'string')) {
    throw new Error(`${field}: expected string[]`)
  }
  return v as string[]
}
