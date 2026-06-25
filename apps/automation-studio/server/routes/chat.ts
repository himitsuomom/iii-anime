import Anthropic from '@anthropic-ai/sdk'
import { Hono } from 'hono'
import { streamSSE } from 'hono/streaming'
import { getClient, MODEL } from '../anthropic.ts'
import { type ChatMessage, INQUIRY_SYSTEM as SYSTEM } from '../lib/inquiry.ts'
import { offlineChatReply } from '../lib/offline.ts'

export const chatRoute = new Hono()

interface ChatBody {
  messages?: ChatMessage[]
}

chatRoute.post('/', async (c) => {
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

  const client = getClient()

  // API-less fallback: no key → stream a rule-based reply in the same SSE shape.
  if (!client) {
    return streamSSE(c, async (stream) => {
      const reply = offlineChatReply(history)
      for (const chunk of reply.match(/[\s\S]{1,12}/g) ?? [reply]) {
        await stream.writeSSE({ event: 'delta', data: JSON.stringify({ text: chunk }) })
        await stream.sleep(20)
      }
      await stream.writeSSE({ event: 'done', data: '{}' })
    })
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
