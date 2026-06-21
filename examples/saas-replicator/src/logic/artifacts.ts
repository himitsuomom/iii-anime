/**
 * Pure artifact contracts and builders (no iii-sdk imports — unit-testable).
 *
 * Each phase produces a typed artifact. Provider output is free-form text, so
 * `parseJsonFromContent` extracts a JSON object when present and the `build*`
 * helpers fill defaults — artifacts are always well-formed, even in stub mode.
 */

export interface DesignTokens {
  colors: string[]
  fonts: string[]
  spacing: number[]
}

export interface ScreenAnalysis {
  screen: string
  components: string[]
  tokens: DesignTokens
  notes?: string
}

export interface Prd {
  target: string
  summary: string
  features: string[]
  dataModel: string[]
}

export interface Implementation {
  target: string
  files: string[]
  notes?: string
}

export interface TestReport {
  total: number
  passed: number
  failed: number
  viaSandbox: boolean
  stdout?: string
}

export interface VisualArtifact {
  format: 'mermaid'
  source: string
}

export interface Deployment {
  url: string
  pwa: boolean
  notes?: string
}

/**
 * Extract a JSON object/array from provider content. Accepts a raw object, a
 * JSON string, or text containing a ```json fenced / first `{...}` block.
 * Returns `{}` when nothing parseable is found (callers apply defaults).
 */
export function parseJsonFromContent(content: unknown): Record<string, unknown> {
  if (content && typeof content === 'object') {
    // Provider responses look like { content: "..." }; unwrap if needed.
    const maybe = content as Record<string, unknown>
    if (typeof maybe.content === 'string') return parseJsonFromContent(maybe.content)
    return maybe
  }
  if (typeof content !== 'string') return {}

  const tryParse = (s: string): Record<string, unknown> | null => {
    try {
      const v = JSON.parse(s)
      return v && typeof v === 'object' ? (v as Record<string, unknown>) : null
    } catch {
      return null
    }
  }

  const direct = tryParse(content.trim())
  if (direct) return direct

  const fenced = content.match(/```(?:json)?\s*([\s\S]*?)```/i)
  if (fenced?.[1]) {
    const v = tryParse(fenced[1].trim())
    if (v) return v
  }

  const brace = content.match(/[{[][\s\S]*[}\]]/)
  if (brace?.[0]) {
    const v = tryParse(brace[0])
    if (v) return v
  }
  return {}
}

const asStringArray = (v: unknown, fallback: string[] = []): string[] => (Array.isArray(v) ? v.map(String) : fallback)

const asNumberArray = (v: unknown, fallback: number[] = []): number[] =>
  Array.isArray(v) ? v.map(Number).filter((n) => !Number.isNaN(n)) : fallback

export function buildDesignTokens(raw: Record<string, unknown>): DesignTokens {
  return {
    colors: asStringArray(raw.colors),
    fonts: asStringArray(raw.fonts),
    spacing: asNumberArray(raw.spacing),
  }
}

export function buildScreenAnalysis(screen: string, raw: Record<string, unknown>): ScreenAnalysis {
  return {
    screen,
    components: asStringArray(raw.components),
    tokens: buildDesignTokens((raw.tokens as Record<string, unknown>) ?? {}),
    notes: typeof raw.notes === 'string' ? raw.notes : undefined,
  }
}

export function buildPrd(target: string, raw: Record<string, unknown>): Prd {
  return {
    target,
    summary: typeof raw.summary === 'string' ? raw.summary : `PRD for ${target}`,
    features: asStringArray(raw.features),
    dataModel: asStringArray(raw.dataModel),
  }
}

export function buildImplementation(target: string, raw: Record<string, unknown>): Implementation {
  return {
    target,
    files: asStringArray(raw.files, ['frontend/app.tsx', 'backend/api.ts']),
    notes: typeof raw.notes === 'string' ? raw.notes : undefined,
  }
}

export function buildDeployment(raw: Record<string, unknown>): Deployment {
  return {
    url: typeof raw.url === 'string' ? raw.url : 'https://example.local',
    pwa: raw.pwa !== false,
    notes: typeof raw.notes === 'string' ? raw.notes : undefined,
  }
}

/** Parse a test summary from sandbox stdout, e.g. `TESTS total=5 passed=4 failed=1`. */
export function parseTestStdout(stdout: string, viaSandbox: boolean): TestReport {
  const num = (key: string): number | undefined => {
    const m = stdout.match(new RegExp(`${key}\\s*=\\s*(\\d+)`, 'i'))
    return m ? Number(m[1]) : undefined
  }
  const total = num('total') ?? 0
  const passed = num('passed') ?? total
  const failed = num('failed') ?? Math.max(0, total - passed)
  return { total, passed, failed, viaSandbox, stdout }
}
