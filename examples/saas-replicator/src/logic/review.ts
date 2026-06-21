/**
 * Pure Supervisor-pattern logic (no iii-sdk imports — unit-testable).
 *
 * A critic role grades an artifact and returns a normalized {score, pass,
 * feedback}. The director uses this to decide whether to accept an artifact or
 * regenerate it with feedback (the Supervisor / review-loop pattern from
 * DESIGN §9). Kept provider-agnostic: works the same whether the critic is
 * Claude (self-critique) or KIMI.
 */

export interface Critique {
  /** Normalized quality score in [0, 1]. */
  score: number
  /** Whether the artifact passed the acceptance threshold. */
  pass: boolean
  /** Actionable feedback used to seed the next round when failing. */
  feedback: string
}

/** Default acceptance threshold (normalized 0..1). */
export const DEFAULT_THRESHOLD = 0.7

/**
 * Normalize a raw critic response into a {@link Critique}. Accepts scores on a
 * 0..1 or 0..10 scale (values > 1 are divided by 10), an explicit boolean
 * `pass`, and free-form `feedback`. Missing/garbage input fails closed
 * (score 0, pass derived from threshold) so a bad critic never auto-approves.
 */
export function parseCritique(raw: Record<string, unknown>, threshold = DEFAULT_THRESHOLD): Critique {
  const rawScore = typeof raw.score === 'number' && Number.isFinite(raw.score) ? raw.score : 0
  const score = clamp01(rawScore > 1 ? rawScore / 10 : rawScore)
  const feedback = typeof raw.feedback === 'string' ? raw.feedback : ''
  // An explicit boolean `pass` wins; otherwise derive it from the score.
  const pass = typeof raw.pass === 'boolean' ? raw.pass : score >= threshold
  return { score, pass, feedback }
}

/** True when the critique clears the bar (explicit pass OR score >= threshold). */
export function accepted(c: Critique, threshold = DEFAULT_THRESHOLD): boolean {
  return c.pass || c.score >= threshold
}

function clamp01(n: number): number {
  if (Number.isNaN(n)) return 0
  return Math.max(0, Math.min(1, n))
}
