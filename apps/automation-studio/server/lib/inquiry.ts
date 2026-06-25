/**
 * Shared customer-inquiry answering. The Hono `/api/chat` route streams tokens
 * (SSE); this module provides the non-streaming variant used by the iii worker
 * function (`ai::answer-inquiry`). Both share the system prompt and the offline
 * FAQ fallback so behavior stays consistent.
 */
import { getClient, MODEL } from '../anthropic.ts'
import { recordInquiry } from './metrics.ts'
import { offlineChatReply } from './offline.ts'

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

export const INQUIRY_SYSTEM = `あなたは日本のECショップのカスタマーサポートAIアシスタントです。
お客様からの問い合わせ（商品の詳細、在庫、配送、返品・交換など）に、丁寧で簡潔な日本語で回答します。
確実でない情報は断定せず、「担当者が確認します」と案内してください。`

export type InquirySource = 'claude' | 'faq'

export interface InquiryResult {
  reply: string
  source: InquirySource
}

/**
 * Produce a single (non-streaming) reply to a customer inquiry. Throws on empty
 * input; returns the FAQ fallback when no API key is configured.
 */
export async function answerInquiry(messages: ChatMessage[]): Promise<InquiryResult> {
  const history = (messages ?? []).filter((m) => m.content?.trim())
  if (history.length === 0) throw new Error('messages が空です。')

  const client = getClient()
  if (!client) {
    recordInquiry()
    return { reply: offlineChatReply(history), source: 'faq' }
  }

  const message = await client.messages.create({
    model: MODEL,
    max_tokens: 1024,
    system: INQUIRY_SYSTEM,
    messages: history.map((m) => ({ role: m.role, content: m.content })),
  })

  if (message.stop_reason === 'refusal') {
    throw new Error('モデルにより応答が拒否されました。')
  }

  const textBlock = message.content.find((b) => b.type === 'text')
  const reply = textBlock && textBlock.type === 'text' ? textBlock.text : ''
  recordInquiry()
  return { reply, source: 'claude' }
}
