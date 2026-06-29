/**
 * API-less fallbacks. When ANTHROPIC_API_KEY is not configured the app still
 * needs to be useful, so these pure-logic helpers produce reasonable output
 * without calling Claude. The same response shapes are used as the AI path.
 */

export interface DescriptionInput {
  productName: string
  features?: string
  keywords?: string
  tone?: string
}

export interface GeneratedDescription {
  title: string
  description: string
  bullets: string[]
  seoKeywords: string[]
}

/** Split a free-text field into trimmed tokens on common JP/EN separators. */
function tokenize(value: string | undefined): string[] {
  if (!value) return []
  return value
    .split(/[\n,、，・/|]+/)
    .map((s) => s.trim())
    .filter(Boolean)
}

function unique(values: string[]): string[] {
  return [...new Set(values.map((v) => v.trim()).filter(Boolean))]
}

export function buildTemplateDescription(input: DescriptionInput): GeneratedDescription {
  const name = input.productName.trim()
  const featureItems = tokenize(input.features)
  const keywordItems = tokenize(input.keywords)

  const title = keywordItems.length > 0 ? `${name}｜${keywordItems.slice(0, 2).join('・')}` : name

  const lead =
    featureItems.length > 0 ? `${featureItems.slice(0, 2).join('・')}が特徴の${name}です。` : `${name}をご紹介します。`
  const description = [
    lead,
    'こだわりの品質で、日常をワンランクアップ。気になった方はこの機会にぜひお試しください。',
    keywordItems.length > 0 ? `「${keywordItems.slice(0, 3).join('」「')}」をお探しの方におすすめです。` : '',
  ]
    .filter(Boolean)
    .join('')

  const bullets =
    featureItems.length > 0
      ? featureItems.slice(0, 5).map((f) => `${f}`)
      : ['高品質で安心の仕上がり', '幅広いシーンで活躍', '届いたらすぐに使える']

  const seoKeywords = unique([...keywordItems, ...tokenize(name), `${name} 通販`, `${name} おすすめ`]).slice(0, 8)

  return { title, description, bullets, seoKeywords }
}

interface FaqEntry {
  keywords: string[]
  answer: string
}

const FAQ: FaqEntry[] = [
  {
    keywords: ['配送', '発送', '届く', '日数', 'いつ', 'お届け', '送料'],
    answer:
      'ご注文後、通常2〜4営業日以内に発送いたします。送料は全国一律でご案内しており、追跡番号は発送時にお送りします。お急ぎの場合は備考欄にご記入ください。',
  },
  {
    keywords: ['返品', '交換', '返金', 'キャンセル'],
    answer:
      '商品到着後7日以内であれば、未使用・未開封のものに限り返品・交換を承ります。不良品の場合は送料当店負担で対応いたしますので、写真を添えてご連絡ください。',
  },
  {
    keywords: ['在庫', '入荷', '再販', 'いつ買える'],
    answer:
      '在庫状況は商品ページに反映しております。品切れの場合も再入荷予定がある商品が多いため、入荷通知をご希望の場合はお気軽にお問い合わせください。',
  },
  {
    keywords: ['支払', '決済', 'カード', '振込', 'コンビニ', 'ペイ'],
    answer:
      'クレジットカード、コンビニ決済、各種QRコード決済に対応しております。分割やあと払いをご希望の場合もご案内できますので、ご希望の方法をお知らせください。',
  },
  {
    keywords: ['サイズ', '寸法', '大きさ', '重さ', '素材'],
    answer:
      '詳細なサイズ・素材は商品ページの仕様欄に記載しております。記載が見当たらない場合は、担当者が確認のうえ折り返しご案内いたしますのでお知らせください。',
  },
]

export function offlineChatReply(messages: { role: string; content: string }[]): string {
  const lastUser = [...messages].reverse().find((m) => m.role === 'user')
  const text = lastUser?.content ?? ''
  const hit = FAQ.find((entry) => entry.keywords.some((k) => text.includes(k)))
  if (hit) return hit.answer
  return 'お問い合わせありがとうございます。内容を担当者が確認のうえ、改めてご回答いたします。配送・返品・在庫・お支払いなど、具体的なご質問があればお知らせください。'
}
