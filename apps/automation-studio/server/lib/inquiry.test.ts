import { beforeEach, describe, expect, it } from 'vitest'
import { answerInquiry } from './inquiry.ts'

beforeEach(() => {
  process.env.ANTHROPIC_API_KEY = ''
})

describe('answerInquiry (offline)', () => {
  it('returns a FAQ reply for a known topic when no API key is configured', async () => {
    const { reply, source } = await answerInquiry([{ role: 'user', content: '配送はいつ届きますか？' }])
    expect(source).toBe('faq')
    expect(reply).toContain('発送')
  })

  it('returns the generic fallback for an unmatched inquiry', async () => {
    const { reply, source } = await answerInquiry([{ role: 'user', content: 'こんにちは' }])
    expect(source).toBe('faq')
    expect(reply.length).toBeGreaterThan(0)
  })

  it('throws when there are no non-empty messages', async () => {
    await expect(answerInquiry([])).rejects.toThrow()
    await expect(answerInquiry([{ role: 'user', content: '   ' }])).rejects.toThrow()
  })
})
