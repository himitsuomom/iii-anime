/**
 * Engine-wired orchestration patterns (DESIGN §9).
 *
 * Pure decision logic lives in `logic/review.ts`; this module wires it to the
 * provider via `callRole`/`callRoleJson`. Two patterns are realized here:
 *
 *  - Supervisor: generate -> critique -> regenerate-with-feedback loop.
 *  - Debate (with graceful degradation): when proposer and opponent resolve to
 *    *different* providers we run a real two-model debate + judge synthesis;
 *    when they collapse to the *same* provider (the Claude-only default) it
 *    degrades to self-critique — one model proposes, critiques itself, revises.
 */

import type { Engine } from './engine'
import { Logger } from './log'
import type { Message } from './logic/prompts'
import { critiquePrompt, debatePrompt, synthesizePrompt } from './logic/prompts'
import { accepted, type Critique, DEFAULT_THRESHOLD, parseCritique } from './logic/review'
import type { ProviderBinding, Role } from './logic/roleBinding'
import { callRoleJson } from './provider'

const logger = new Logger(undefined, 'patterns')

export interface SupervisedOptions<T> {
  /** Role that produces the artifact (e.g. `director`). */
  role: Role
  /** Role that grades it (often the same role for self-supervision). */
  criticRole: Role
  /** What the artifact is about (used in the critique prompt). */
  target: string
  /** Build the initial prompt; round > 0 also receives prior feedback. */
  prompt: (feedback?: string) => Message[]
  /** Turn raw provider JSON into the typed artifact (reuses `build*` helpers). */
  build: (raw: Record<string, unknown>) => T
  maxRounds?: number
  threshold?: number
}

export interface SupervisedResult<T> {
  artifact: T
  rounds: number
  critiques: Critique[]
}

/**
 * Supervisor loop: produce an artifact, have the critic grade it, and
 * regenerate with feedback until it passes or `maxRounds` is hit. Always
 * returns the best (final) artifact so the pipeline never stalls.
 */
export async function supervisedGenerate<T>(engine: Engine, opts: SupervisedOptions<T>): Promise<SupervisedResult<T>> {
  const maxRounds = opts.maxRounds ?? 2
  const threshold = opts.threshold ?? DEFAULT_THRESHOLD
  const critiques: Critique[] = []
  let feedback: string | undefined
  let artifact!: T

  for (let round = 1; round <= maxRounds; round++) {
    artifact = opts.build(await callRoleJson(engine, opts.role, opts.prompt(feedback)))
    const critique = parseCritique(
      await callRoleJson(engine, opts.criticRole, critiquePrompt(opts.target, artifact)),
      threshold,
    )
    critiques.push(critique)
    logger.info('Supervisor round', { round, role: opts.role, score: critique.score, pass: critique.pass })
    if (accepted(critique, threshold)) return { artifact, rounds: round, critiques }
    feedback = critique.feedback
  }
  return { artifact, rounds: maxRounds, critiques }
}

export interface DebateOptions {
  question: string
  proposerRole: Role
  opponentRole: Role
  judgeRole: Role
}

export interface DebateResult {
  mode: 'debate' | 'self-critique'
  answer: string
  rounds: number
}

/**
 * Run a debate when the two roles resolve to distinct providers; otherwise
 * degrade to self-critique. This mirrors progressive enhancement: Claude-only
 * (one provider) self-critiques; adding `provider-kimi` upgrades it to a real
 * two-model debate automatically.
 */
export async function debateOrCritique(engine: Engine, opts: DebateOptions): Promise<DebateResult> {
  const [proposer, opponent] = await Promise.all([
    engine.call<ProviderBinding>('provider::resolve', { role: opts.proposerRole }),
    engine.call<ProviderBinding>('provider::resolve', { role: opts.opponentRole }),
  ])

  if (proposer.provider !== opponent.provider) {
    logger.info('Debate (distinct providers)', { a: proposer.provider, b: opponent.provider })
    const [posA, posB] = await Promise.all([
      callRoleJson(engine, opts.proposerRole, debatePrompt(opts.question, 'for')),
      callRoleJson(engine, opts.opponentRole, debatePrompt(opts.question, 'against')),
    ])
    const decision = await callRoleJson(engine, opts.judgeRole, synthesizePrompt(opts.question, [posA, posB]))
    return { mode: 'debate', answer: answerOf(decision), rounds: 2 }
  }

  // Single provider -> self-critique: propose, critique own answer, revise.
  logger.info('Self-critique (single provider)', { provider: proposer.provider })
  const draft = await callRoleJson(engine, opts.proposerRole, debatePrompt(opts.question))
  const critique = parseCritique(await callRoleJson(engine, opts.judgeRole, critiquePrompt(opts.question, draft)))
  if (accepted(critique)) return { mode: 'self-critique', answer: answerOf(draft), rounds: 1 }
  const revised = await callRoleJson(
    engine,
    opts.proposerRole,
    debatePrompt(`${opts.question} (revise: ${critique.feedback})`),
  )
  return { mode: 'self-critique', answer: answerOf(revised), rounds: 2 }
}

function answerOf(raw: Record<string, unknown>): string {
  if (typeof raw.answer === 'string' && raw.answer) return raw.answer
  return JSON.stringify(raw)
}
