import crypto from 'node:crypto'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { webhooksRoute } from './webhooks.ts'

const ORDER = { id: 555, financial_status: 'paid', currency: 'JPY', total_price: '900', line_items: [] }

function post(body: string, headers: Record<string, string> = {}) {
  return webhooksRoute.request('/shopify/orders', {
    method: 'POST',
    body,
    headers: { 'content-type': 'application/json', ...headers },
  })
}

describe('POST /shopify/orders', () => {
  beforeEach(() => {
    process.env.SHOPIFY_WEBHOOK_SECRET = ''
  })
  afterEach(() => {
    process.env.SHOPIFY_WEBHOOK_SECRET = ''
  })

  it('acks 200 with no worker connected (enqueued=false)', async () => {
    const res = await post(JSON.stringify(ORDER))
    expect(res.status).toBe(200)
    const data = await res.json()
    expect(data).toMatchObject({ ok: true, id: '555', enqueued: false })
  })

  it('returns 400 on invalid JSON', async () => {
    const res = await post('{not json')
    expect(res.status).toBe(400)
  })

  it('returns 400 when the order has no id', async () => {
    const res = await post(JSON.stringify({ total_price: '100' }))
    expect(res.status).toBe(400)
  })

  it('rejects a bad signature when a secret is configured', async () => {
    process.env.SHOPIFY_WEBHOOK_SECRET = 'sekret'
    const res = await post(JSON.stringify(ORDER), { 'X-Shopify-Hmac-Sha256': 'wrong' })
    expect(res.status).toBe(401)
  })

  it('accepts a valid signature when a secret is configured', async () => {
    process.env.SHOPIFY_WEBHOOK_SECRET = 'sekret'
    const body = JSON.stringify(ORDER)
    const sig = crypto.createHmac('sha256', 'sekret').update(body).digest('base64')
    const res = await post(body, { 'X-Shopify-Hmac-Sha256': sig })
    expect(res.status).toBe(200)
  })
})
