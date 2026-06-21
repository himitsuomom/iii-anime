export interface GeneratedDescription {
  title: string
  description: string
  bullets: string[]
  seoKeywords: string[]
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

export type Quadrant = 'doing' | 'deciding' | 'delegating' | 'designing'

export interface Task {
  id: string
  title: string
  quadrant: Quadrant
}

export const QUADRANTS: { id: Quadrant; label: string; hint: string; color: string }[] = [
  { id: 'doing', label: 'Doing（実行）', hint: '自分の手を動かす作業', color: 'var(--color-doing)' },
  { id: 'deciding', label: 'Deciding（決定）', hint: '判断・意思決定', color: 'var(--color-deciding)' },
  { id: 'delegating', label: 'Delegating（委任）', hint: 'AI/VAに任せられる', color: 'var(--color-delegating)' },
  { id: 'designing', label: 'Designing（設計）', hint: '仕組み・戦略づくり', color: 'var(--color-designing)' },
]
