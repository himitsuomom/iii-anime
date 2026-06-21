import assert from 'node:assert/strict'
import { test } from 'node:test'
import { MemoryEngine } from '../src/adapters/memoryEngine'
import { buildPrd, type Prd } from '../src/logic/artifacts'
import { prdPrompt } from '../src/logic/prompts'
import { accepted, parseCritique } from '../src/logic/review'
import { registerOrchestrator } from '../src/orchestrator'
import { debateOrCritique, supervisedGenerate } from '../src/patterns'

process.env.SAAS_PROVIDER_MODE = 'stub'

test('parseCritique normalizes 0..10 scores and derives pass from threshold', () => {
  assert.equal(parseCritique({ score: 8 }).score, 0.8) // 0..10 -> 0..1
  assert.equal(parseCritique({ score: 0.9 }).score, 0.9) // already 0..1
  assert.equal(parseCritique({ score: 8 }).pass, true) // 0.8 >= 0.7
  assert.equal(parseCritique({ score: 3 }).pass, false) // 0.3 < 0.7
  // Explicit boolean pass wins over the score-derived value.
  assert.equal(parseCritique({ score: 1, pass: false }).pass, false)
  // Garbage fails closed.
  assert.equal(parseCritique({}).score, 0)
  assert.equal(accepted(parseCritique({})), false)
})

test('supervisedGenerate accepts on round 1 in stub mode', async () => {
  const engine = new MemoryEngine()
  registerOrchestrator(engine)

  const result = await supervisedGenerate<Prd>(engine, {
    role: 'director',
    criticRole: 'director',
    target: 'Trello',
    prompt: (feedback) => prdPrompt('Trello', feedback ?? 'PWA'),
    build: (raw) => buildPrd('Trello', raw),
  })

  assert.equal(result.rounds, 1) // stub critic passes immediately
  assert.equal(result.critiques.length, 1)
  assert.ok(result.critiques[0]?.pass)
  assert.equal(result.artifact.target, 'Trello')
  assert.ok(result.artifact.features.length > 0)
})

test('debateOrCritique degrades to self-critique with a single provider (Claude-only/stub)', async () => {
  const engine = new MemoryEngine() // no provider-kimi
  registerOrchestrator(engine)

  const result = await debateOrCritique(engine, {
    question: 'What architecture should we use to rebuild Trello?',
    proposerRole: 'director',
    opponentRole: 'swarm',
    judgeRole: 'director',
  })

  assert.equal(result.mode, 'self-critique')
  assert.ok(result.answer.length > 0)
})

test('debateOrCritique upgrades to a real debate when providers differ', async () => {
  // live mode + provider-kimi present -> proposer(anthropic) vs opponent(kimi).
  process.env.SAAS_PROVIDER_MODE = 'live'
  try {
    const engine = new MemoryEngine([{ name: 'provider-kimi' }])
    registerOrchestrator(engine)
    engine.register('provider-anthropic::messages', async () => ({
      content: JSON.stringify({ answer: 'monolith', rationale: 'simple' }),
    }))
    engine.register('provider-kimi::messages', async () => ({
      content: JSON.stringify({ answer: 'microservices', rationale: 'scale' }),
    }))

    const result = await debateOrCritique(engine, {
      question: 'What architecture should we use to rebuild Trello?',
      proposerRole: 'director', // anthropic
      opponentRole: 'swarm', // kimi
      judgeRole: 'director',
    })

    assert.equal(result.mode, 'debate')
    assert.equal(result.rounds, 2)
    assert.ok(result.answer.length > 0)
  } finally {
    process.env.SAAS_PROVIDER_MODE = 'stub'
  }
})
