import Anthropic from '@anthropic-ai/sdk'
import { Hono } from 'hono'
import { getClient, MODEL } from '../anthropic.ts'

export const generateRoute = new Hono()

interface GenerateBody {
  productName?: string
  features?: string
  keywords?: string
  tone?: string
}

/** Structured shape Claude is constrained to return. */
const OUTPUT_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  properties: {
    title: { type: 'string', description: 'SEOを意識した魅力的な商品タイトル（全角40文字以内）' },
    description: { type: 'string', description: '商品説明本文。3〜5文の説得力のある日本語。' },
    bullets: {
      type: 'array',
      description: '購入者が一目で価値を理解できる箇条書き（3〜5個）',
      items: { type: 'string' },
    },
    seoKeywords: {
      type: 'array',
      description: '検索流入を狙うSEOキーワード（5〜8個）',
      items: { type: 'string' },
    },
  },
  required: ['title', 'description', 'bullets', 'seoKeywords'],
} as const

const SYSTEM = `あなたは日本のEC（電子商取引・転売）事業者を支援するプロのコピーライター兼SEO担当です。
与えられた商品情報から、検索に強く、購買意欲を高める日本語の商品ページ用テキストを作成します。
誇大広告や虚偽の効能は書かず、事実に基づいた訴求を行ってください。`

generateRoute.post('/', async (c) => {
  const client = getClient()
  if (!client) {
    return c.json({ error: 'ANTHROPIC_API_KEY が設定されていません。.env に API キーを設定してください。' }, 503)
  }

  let body: GenerateBody
  try {
    body = await c.req.json<GenerateBody>()
  } catch {
    return c.json({ error: 'リクエストボディの JSON が不正です。' }, 400)
  }

  const productName = body.productName?.trim()
  if (!productName) {
    return c.json({ error: '商品名（productName）は必須です。' }, 400)
  }

  const userPrompt = [
    `商品名: ${productName}`,
    body.features?.trim() ? `特徴・仕様: ${body.features.trim()}` : null,
    body.keywords?.trim() ? `狙いたいキーワード: ${body.keywords.trim()}` : null,
    `トーン: ${body.tone?.trim() || 'プロフェッショナルかつ親しみやすい'}`,
  ]
    .filter(Boolean)
    .join('\n')

  try {
    const message = await client.messages.create({
      model: MODEL,
      max_tokens: 2048,
      system: SYSTEM,
      output_config: { format: { type: 'json_schema', schema: OUTPUT_SCHEMA } },
      messages: [{ role: 'user', content: userPrompt }],
    })

    if (message.stop_reason === 'refusal') {
      return c.json({ error: 'リクエストはモデルにより拒否されました。入力内容を見直してください。' }, 422)
    }

    const textBlock = message.content.find((b) => b.type === 'text')
    if (!textBlock || textBlock.type !== 'text') {
      return c.json({ error: 'モデルからテキスト応答が得られませんでした。' }, 502)
    }

    const result = JSON.parse(textBlock.text)
    return c.json({ result })
  } catch (err) {
    return c.json({ error: toErrorMessage(err) }, errorStatus(err))
  }
})

function toErrorMessage(err: unknown): string {
  if (err instanceof Anthropic.APIError) return `Claude API エラー (${err.status ?? '???'}): ${err.message}`
  if (err instanceof Error) return err.message
  return '不明なエラーが発生しました。'
}

function errorStatus(err: unknown): 429 | 500 | 502 {
  if (err instanceof Anthropic.RateLimitError) return 429
  if (err instanceof Anthropic.APIError) return 502
  return 500
}
