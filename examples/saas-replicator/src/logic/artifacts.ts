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

/** One generated source file (relative path + contents). */
export interface GeneratedFile {
  path: string
  content: string
}

/** A generated codebase: real file contents plus the entry test to execute. */
export interface Codebase {
  target: string
  files: GeneratedFile[]
  /** Relative path of the test program the executor runs (prints a TESTS line). */
  testFile: string
}

export interface TestReport {
  total: number
  passed: number
  failed: number
  /** Back-compat flag: true when the suite ran in iii-sandbox. */
  viaSandbox: boolean
  /** Where the suite ran: isolated microVM, local child process, or role fallback. */
  executor?: 'sandbox' | 'local' | 'role'
  /** Number of files materialized into the workspace before running. */
  filesGenerated?: number
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

/**
 * Reject paths that would escape the workspace: absolute paths, `..` segments,
 * Windows drive letters, or backslashes. Kept pure here (no node deps) so both
 * the artifact builder and `workspace.ts` share one rule.
 */
export function isSafeRelativePath(p: string): boolean {
  if (typeof p !== 'string' || p.length === 0) return false
  if (p.startsWith('/') || p.startsWith('\\') || /^[a-zA-Z]:/.test(p)) return false
  return !p.split(/[/\\]/).some((seg) => seg === '..')
}

/** Minimal runnable scaffold used when the provider returns no usable files. */
const DEFAULT_CODEBASE_FILES: GeneratedFile[] = [
  { path: 'src/app.mjs', content: 'export const add = (a, b) => a + b\n' },
  {
    path: 'test.mjs',
    content: [
      "import { add } from './src/app.mjs'",
      'const cases = [add(1, 1) === 2, add(2, 2) === 4]',
      'const total = cases.length',
      'const passed = cases.filter(Boolean).length',
      "console.log('TESTS total=' + total + ' passed=' + passed + ' failed=' + (total - passed))",
      '',
    ].join('\n'),
  },
]

/**
 * Build a runnable codebase from provider output. Accepts `files: [{path,
 * content}]`; drops entries with unsafe paths or non-string content. Falls back
 * to {@link DEFAULT_CODEBASE_FILES} so the Phase 3 executor always has a real,
 * runnable test to run.
 */
export function buildCodebase(target: string, raw: Record<string, unknown>): Codebase {
  const rawFiles = Array.isArray(raw.files) ? raw.files : []
  const files: GeneratedFile[] = rawFiles
    .map((f) => f as Record<string, unknown>)
    .filter((f) => f && typeof f.path === 'string' && typeof f.content === 'string' && isSafeRelativePath(f.path))
    .map((f) => ({ path: f.path as string, content: f.content as string }))

  const usable = files.length > 0 ? files : DEFAULT_CODEBASE_FILES
  const requested = typeof raw.testFile === 'string' && isSafeRelativePath(raw.testFile) ? raw.testFile : undefined
  // Use the requested test file only if it was actually materialized.
  const testFile = requested && usable.some((f) => f.path === requested) ? requested : pickTestFile(usable)
  return { target, files: usable, testFile }
}

/** Choose the entry test: a file named like a test, else the first file. */
function pickTestFile(files: GeneratedFile[]): string {
  const byName = files.find(
    (f) => /(^|\/)test[^/]*\.(mjs|js|cjs)$/i.test(f.path) || /\.test\.(mjs|js|cjs)$/i.test(f.path),
  )
  return (byName ?? files[0])?.path ?? 'test.mjs'
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
