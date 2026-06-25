import { beforeEach, describe, expect, it } from 'vitest'
import { type IIIEngine, registerAiFunctions } from './iii-worker.ts'

beforeEach(() => {
  process.env.ANTHROPIC_API_KEY = ''
})

/** Records registered functions so we can invoke them directly (no engine). */
class FakeEngine implements IIIEngine {
  functions = new Map<string, (data: unknown) => Promise<unknown>>()
  registerFunction(id: string, handler: (data: unknown) => Promise<unknown>): unknown {
    this.functions.set(id, handler)
    return { id }
  }

  /** Get a registered handler, throwing if it is missing. */
  handler(id: string): (data: unknown) => Promise<unknown> {
    const fn = this.functions.get(id)
    if (!fn) throw new Error(`function not registered: ${id}`)
    return fn
  }
}

describe('registerAiFunctions', () => {
  it('registers both AI functions', () => {
    const engine = new FakeEngine()
    registerAiFunctions(engine)
    expect([...engine.functions.keys()].sort()).toEqual(['ai::answer-inquiry', 'ai::describe-product'])
  })

  it('ai::describe-product returns a description (template offline) with source', async () => {
    const engine = new FakeEngine()
    registerAiFunctions(engine)
    const handler = engine.handler('ai::describe-product')
    const out = (await handler({ productName: 'テスト商品', keywords: 'a,b' })) as Record<string, unknown>
    expect(out.title).toBeTruthy()
    expect(out.source).toBe('template')
    expect(Array.isArray(out.bullets)).toBe(true)
  })

  it('ai::describe-product unwraps an HTTP ApiRequest envelope', async () => {
    const engine = new FakeEngine()
    registerAiFunctions(engine)
    const handler = engine.handler('ai::describe-product')
    const direct = await handler({ productName: 'X' })
    const wrapped = await handler({ method: 'POST', headers: {}, body: { productName: 'X' } })
    expect(wrapped).toEqual(direct)
  })

  it('ai::answer-inquiry returns a reply with source', async () => {
    const engine = new FakeEngine()
    registerAiFunctions(engine)
    const handler = engine.handler('ai::answer-inquiry')
    const out = (await handler({ messages: [{ role: 'user', content: '返品できますか？' }] })) as Record<
      string,
      unknown
    >
    expect(out.source).toBe('faq')
    expect(typeof out.reply).toBe('string')
  })
})
