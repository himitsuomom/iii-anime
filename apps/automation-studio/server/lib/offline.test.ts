import { describe, expect, it } from 'vitest'
import { buildTemplateDescription, offlineChatReply } from './offline.ts'

describe('buildTemplateDescription', () => {
  it('derives title, bullets and SEO keywords from the inputs', () => {
    const r = buildTemplateDescription({
      productName: '真鍮製デスクランプ',
      features: '真鍮素材、調光機能、USB給電',
      keywords: 'アンティーク,間接照明',
    })
    expect(r.title).toBe('真鍮製デスクランプ｜アンティーク・間接照明')
    expect(r.bullets).toEqual(['真鍮素材', '調光機能', 'USB給電'])
    expect(r.seoKeywords).toContain('アンティーク')
    expect(r.seoKeywords).toContain('真鍮製デスクランプ 通販')
    expect(r.seoKeywords.length).toBeLessThanOrEqual(8)
  })

  it('falls back to generic bullets and a bare title with no extra input', () => {
    const r = buildTemplateDescription({ productName: 'テスト商品' })
    expect(r.title).toBe('テスト商品')
    expect(r.bullets).toHaveLength(3)
    expect(r.description).toContain('テスト商品')
  })

  it('deduplicates SEO keywords', () => {
    const r = buildTemplateDescription({ productName: 'A', keywords: 'A,A,B' })
    expect(new Set(r.seoKeywords).size).toBe(r.seoKeywords.length)
  })
})

describe('offlineChatReply', () => {
  it('matches shipping questions', () => {
    const a = offlineChatReply([{ role: 'user', content: '配送は何日で届きますか？' }])
    expect(a).toContain('発送')
  })

  it('matches return questions', () => {
    const a = offlineChatReply([{ role: 'user', content: '返品はできますか？' }])
    expect(a).toContain('返品')
  })

  it('uses the most recent user message', () => {
    const a = offlineChatReply([
      { role: 'user', content: '在庫ありますか' },
      { role: 'assistant', content: '...' },
      { role: 'user', content: '支払い方法は？' },
    ])
    expect(a).toContain('決済')
  })

  it('falls back to a generic reply when nothing matches', () => {
    const a = offlineChatReply([{ role: 'user', content: 'こんにちは' }])
    expect(a).toContain('担当者が確認')
  })
})
