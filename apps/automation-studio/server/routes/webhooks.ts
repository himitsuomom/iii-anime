/**
 * Inbound platform webhooks. Currently: Shopify order events.
 *
 * Follows the standard ingestion pattern: verify the HMAC signature, acknowledge
 * fast (200), then hand the work to the engine's durable queue for asynchronous,
 * idempotent persistence (orders::ingest keys by order id). Heavy work never
 * happens inline, so Shopify's few-second ack window is always met.
 */
import { Hono } from 'hono'
import { getWorker } from '../iii-worker.ts'
import { mapShopifyOrder, verifyShopifyHmac } from '../lib/shopify-order.ts'

export const webhooksRoute = new Hono()

webhooksRoute.post('/shopify/orders', async (c) => {
  const raw = await c.req.text()

  // Verify the signature when a secret is configured. With no secret (local dev)
  // we accept and log, so the endpoint is testable without Shopify credentials.
  const secret = process.env.SHOPIFY_WEBHOOK_SECRET ?? ''
  if (secret) {
    const sig = c.req.header('X-Shopify-Hmac-Sha256')
    if (!verifyShopifyHmac(raw, sig, secret)) {
      return c.json({ error: 'invalid signature' }, 401)
    }
  }

  let payload: Record<string, unknown>
  try {
    payload = JSON.parse(raw)
  } catch {
    return c.json({ error: 'invalid json' }, 400)
  }

  const order = mapShopifyOrder(payload)
  if (!order.id) return c.json({ error: 'missing order id' }, 400)

  // Acknowledge immediately; enqueue persistence asynchronously (idempotent by id).
  const worker = getWorker()
  if (worker) {
    void worker
      .trigger({
        function_id: 'orders::ingest',
        payload: order,
        action: { type: 'enqueue', queue: 'default' },
      })
      .catch((err) => console.error('orders::ingest enqueue failed:', err))
  }

  return c.json({ ok: true, id: order.id, enqueued: Boolean(worker) })
})
