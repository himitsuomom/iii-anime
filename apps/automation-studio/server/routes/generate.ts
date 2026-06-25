import { Hono } from 'hono'
import { DescribeError, generateDescription } from '../lib/describe.ts'
import type { DescriptionInput } from '../lib/offline.ts'

export const generateRoute = new Hono()

generateRoute.post('/', async (c) => {
  let body: DescriptionInput
  try {
    body = await c.req.json<DescriptionInput>()
  } catch {
    return c.json({ error: 'リクエストボディの JSON が不正です。' }, 400)
  }

  try {
    const { result, source } = await generateDescription(body)
    return c.json({ result, source })
  } catch (err) {
    if (err instanceof DescribeError) return c.json({ error: err.message }, err.status)
    return c.json({ error: '不明なエラーが発生しました。' }, 500)
  }
})
