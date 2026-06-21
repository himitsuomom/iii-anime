// Constants distilled from ai_ecommerce_business_report.md (§6.3, §8.1, §11.1, §11.2).
// Used by the offline (API-less) tools: ROI simulator, roadmap, profit calculator.

export interface PlatformPreset {
  id: string
  label: string
  /** Total selling fee as a percentage of the sale price. */
  feePercent: number
}

// General marketplace fee rates (editable in the UI). Approximate, JP-market oriented.
export const PLATFORM_PRESETS: PlatformPreset[] = [
  { id: 'mercari', label: 'メルカリ', feePercent: 10 },
  { id: 'amazon', label: 'Amazon', feePercent: 15 },
  { id: 'rakuten', label: '楽天市場', feePercent: 12 },
  { id: 'yahoo', label: 'Yahoo!フリマ', feePercent: 5 },
  { id: 'ebay', label: 'eBay', feePercent: 13 },
  { id: 'etsy', label: 'Etsy', feePercent: 6.5 },
  { id: 'base', label: 'BASE / 自社', feePercent: 3 },
  { id: 'custom', label: 'カスタム', feePercent: 10 },
]

export interface RoiPhase {
  id: string
  label: string
  tools: string
  monthlyCostJpy: [number, number]
  expectedRoi: string
  /** Estimated reduction in operating hours, as a fraction range. */
  hoursSaved: [number, number]
}

// §6.3 / §8.1 phase table, costs converted to JPY (≈¥150/USD) for a JP audience.
export const ROI_PHASES: RoiPhase[] = [
  {
    id: 'startup',
    label: '起業期（検証）',
    tools: 'ChatGPT / Claude + Canva + Shopify(無料)',
    monthlyCostJpy: [0, 7500],
    expectedRoi: '業務時間 −50%',
    hoursSaved: [0.4, 0.5],
  },
  {
    id: 'growth',
    label: '成長期（拡張）',
    tools: '上記 + Jasper + Tidio + Klaviyo',
    monthlyCostJpy: [15000, 30000],
    expectedRoi: '収益 +20〜30%',
    hoursSaved: [0.5, 0.6],
  },
  {
    id: 'scale',
    label: 'スケール期（自動化）',
    tools: '上記 + PODtomatic / Optifai + Salesforce',
    monthlyCostJpy: [45000, 75000],
    expectedRoi: '収益 +40〜60%',
    hoursSaved: [0.6, 0.7],
  },
  {
    id: 'optimize',
    label: '最適化期（AI最大化）',
    tools: 'フルスタック + カスタムAI開発',
    monthlyCostJpy: [75000, 300000],
    expectedRoi: '収益 +100%以上',
    hoursSaved: [0.7, 0.8],
  },
]

export interface RoadmapStep {
  id: string
  period: string
  title: string
  actions: string[]
  cost: string
  outcome: string
}

// §11.2 startup roadmap.
export const ROADMAP_STEPS: RoadmapStep[] = [
  {
    id: 'week1',
    period: 'Week 1',
    title: '基盤構築',
    actions: ['Claude / ChatGPT の有料プランを契約する', '最も時間のかかっている1業務を特定する（例: 商品説明作成）'],
    cost: '$20〜30',
    outcome: '業務理解の深化',
  },
  {
    id: 'week2-4',
    period: 'Week 2-4',
    title: 'パイロット実施',
    actions: ['選んだ1業務をAIに実行させる', '成功基準を設定し効果を測定する（例: 1時間→15分）'],
    cost: '$20〜30',
    outcome: '時間 −50〜80%',
  },
  {
    id: 'month2-3',
    period: 'Month 2-3',
    title: '拡張と自動化',
    actions: ['次の業務にAIを適用する', 'Zapier等でワークフローを連携・自動化する'],
    cost: '$50〜100',
    outcome: '業務時間 −50%',
  },
  {
    id: 'month3-6',
    period: 'Month 3-6',
    title: 'スケールと最適化',
    actions: ['ROIの高いツールを優先する', '浮いた時間と資金を新規顧客獲得へ投資する'],
    cost: '$100〜300',
    outcome: '収益 +20〜50%',
  },
  {
    id: 'month6',
    period: 'Month 6+',
    title: '高度化と差別化',
    actions: ['独自のAIワークフローを構築する', '独自データ・ブランド・顧客関係で差別化する'],
    cost: '$300〜1,000',
    outcome: '収益 +50〜100%',
  },
]

// §11.1 five principles.
export const PRINCIPLES: { title: string; body: string }[] = [
  { title: '①「完全自動化」ではなく「80%自動化」を狙う', body: '苦手な20%（品質・判断・差別化）は人が仕上げる。' },
  { title: '②「仕組み」を先に作り「コンテンツ」を後から量産', body: '収益モデル→ターゲット→量産→改善の順で設計する。' },
  { title: '③ 1つの領域に集中する', body: '1業務で成功体験を得てから横展開するのが最短。' },
  { title: '④ データ駆動のPDCAを回す', body: '時間削減・収益・コストを数値で測定し改善する。' },
  { title: '⑤ ツールは2つまでに絞り習熟度を上げる', body: 'メイン1つ＋補助1つ。数より使いこなしを優先。' },
]
