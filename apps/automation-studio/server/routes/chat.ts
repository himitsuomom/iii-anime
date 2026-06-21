import Anthropic from '@anthropic-ai/sdk'
import { Hono } from 'hono'
import { streamSSE } from 'hono/streaming'
import { getClient, MODEL } from '../anthropic.ts'

export const chatRoute = new Hono()

interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

interface ChatBody {
  messages?: ChatMessage[]
}

const SYSTEM = `あなたは日本のECショップのカスタマーサポートAIアシスタントです。
お客様からの問い合わせ（商品の詳細、在庫、配送、返品・交換など）に、丁寧で簡潔な日本語で回答します。
確実でない情報は断定せず、「担当者が確認します」と案内してください。`

chatRoute.post('/', async (c) => {
  const client = getClient()
  if (!client) {
    return c.json({ error: 'ANTHROPIC_API_KEY が設定されていません。.env に API キーを設定してください。' }, 503)
  }

  let body: ChatBody
  try {
    body = await c.req.json<ChatBody>()
  } catch {
    return c.json({ error: 'リクエストボディの JSON が不正です。' }, 400)
  }

  const history = (body.messages ?? []).filter((m) => m.content?.trim())
  if (history.length === 0) {
    return c.json({ error: 'messages が空です。' }, 400)
  }

  return streamSSE(c, async (stream) => {
    try {
      const ms = client.messages.stream({
        model: MODEL,
        max_tokens: 1024,
        system: SYSTEM,
        messages: history.map((m) => ({ role: m.role, content: m.content })),
      })

      for await (const event of ms) {
        if (event.type === 'content_block_delta' && event.delta.type === 'text_delta') {
          await stream.writeSSE({ event: 'delta', data: JSON.stringify({ text: event.delta.text }) })
        }
      }

      const final = await ms.finalMessage()
      if (final.stop_reason === 'refusal') {
        await stream.writeSSE({ event: 'error', data: JSON.stringify({ error: 'モデルにより応答が拒否されました。' }) })
      }
      await stream.writeSSE({ event: 'done', data: '{}' })
    } catch (err) {
      const error =
        err instanceof Anthropic.APIError ? `Claude API エラー: ${err.message}` : '応答の生成に失敗しました。'
      await stream.writeSSE({ event: 'error', data: JSON.stringify({ error }) })
    }
  })
})
