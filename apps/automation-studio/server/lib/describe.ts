/**
 * Shared product-description generation. Used by both the Hono HTTP route
 * (`routes/generate.ts`) and the iii worker function (`ai::describe-product`),
 * so the two entry points stay in lockstep. Falls back to the offline template
 * when no ANTHROPIC_API_KEY is configured.
 */
import Anthropic from '@anthropic-ai/sdk'
import { getClient, MODEL } from '../anthropic.ts'
import { recordDescription } from './metrics.ts'
import { buildTemplateDescription, type DescriptionInput, type GeneratedDescription } from './offline.ts'

/** Structured shape Claude is constrained to return. Exported for the worker's response_format. */
export const DESCRIBE_OUTPUT_SCHEMA = {
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

export type DescribeSource = 'claude' | 'template'

export interface DescribeResult {
  result: GeneratedDescription
  source: DescribeSource
}

/** Error with an HTTP status the route can surface directly. */
export class DescribeError extends Error {
  constructor(
    message: string,
    public status: 400 | 422 | 429 | 500 | 502,
  ) {
    super(message)
    this.name = 'DescribeError'
  }
}

/**
 * Generate a product description. Throws {@link DescribeError} (with an HTTP
 * status) on invalid input or upstream failure; returns the template fallback
 * when no API key is present.
 */
export async function generateDescription(body: Partial<DescriptionInput>): Promise<DescribeResult> {
  const productName = body.productName?.trim()
  if (!productName) throw new DescribeError('商品名（productName）は必須です。', 400)

  const client = getClient()
  if (!client) {
    recordDescription()
    return { result: buildTemplateDescription({ ...body, productName }), source: 'template' }
  }

  const userPrompt = [
    `商品名: ${productName}`,
    body.features?.trim() ? `特徴・仕様: ${body.features.trim()}` : null,
    body.keywords?.trim() ? `狙いたいキーワード: ${body.keywords.trim()}` : null,
    `トーン: ${body.tone?.trim() || 'プロフェッショナルかつ親しみやすい'}`,
  ]
    .filter(Boolean)
    .join('\n')

  let message: Anthropic.Message
  try {
    message = await client.messages.create({
      model: MODEL,
      max_tokens: 2048,
      system: SYSTEM,
      output_config: { format: { type: 'json_schema', schema: DESCRIBE_OUTPUT_SCHEMA } },
      messages: [{ role: 'user', content: userPrompt }],
    })
  } catch (err) {
    throw new DescribeError(toErrorMessage(err), errorStatus(err))
  }

  if (message.stop_reason === 'refusal') {
    throw new DescribeError('リクエストはモデルにより拒否されました。入力内容を見直してください。', 422)
  }
  if (message.stop_reason === 'max_tokens') {
    throw new DescribeError('出力が長すぎて途中で打ち切られました。入力を短くして再試行してください。', 502)
  }

  const textBlock = message.content.find((b) => b.type === 'text')
  if (!textBlock || textBlock.type !== 'text') {
    throw new DescribeError('モデルからテキスト応答が得られませんでした。', 502)
  }

  let result: GeneratedDescription
  try {
    result = JSON.parse(textBlock.text) as GeneratedDescription
  } catch {
    throw new DescribeError('モデル応答の解析に失敗しました。もう一度お試しください。', 502)
  }
  recordDescription()
  return { result, source: 'claude' }
}

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
