import { beforeEach, describe, expect, it } from 'vitest'
import { DescribeError, generateDescription } from './describe.ts'

// These tests run offline: with no ANTHROPIC_API_KEY the shared generator must
// fall back to the deterministic template (source: 'template').
beforeEach(() => {
  process.env.ANTHROPIC_API_KEY = ''
})

describe('generateDescription (offline)', () => {
  it('returns a template result when no API key is configured', async () => {
    const { result, source } = await generateDescription({
      productName: '真鍮製デスクランプ',
      features: '真鍮素材、調光機能',
      keywords: 'アンティーク,間接照明',
    })
    expect(source).toBe('template')
    expect(result.title).toContain('真鍮製デスクランプ')
    expect(result.bullets.length).toBeGreaterThan(0)
    expect(result.seoKeywords.length).toBeGreaterThan(0)
  })

  it('throws DescribeError(400) when productName is missing', async () => {
    await expect(generateDescription({ productName: '  ' })).rejects.toBeInstanceOf(DescribeError)
    await expect(generateDescription({ productName: '' })).rejects.toMatchObject({ status: 400 })
  })
})
