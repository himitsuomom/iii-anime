/**
 * Pure helpers for ingesting Shopify order webhooks: HMAC verification and
 * mapping the Shopify order payload to the shared `Order` contract shape
 * (packages/contracts). No engine/network dependency — unit-testable offline.
 */
import crypto from 'node:crypto'

export interface Money {
  amount: number // minor units (e.g. 1200 = ¥1,200 for JPY)
  currency: string
}

export interface OrderItem {
  sku: string
  quantity: number
  unitPrice: Money
}

export interface Order {
  id: string
  status: string
  items: OrderItem[]
  total: Money
  createdAt: string
}

/** ISO 4217 zero-decimal currencies (amounts are already in major = minor units). */
const ZERO_DECIMAL = new Set([
  'JPY',
  'KRW',
  'VND',
  'CLP',
  'ISK',
  'XOF',
  'XAF',
  'BIF',
  'DJF',
  'GNF',
  'KMF',
  'MGA',
  'PYG',
  'RWF',
  'UGX',
  'VUV',
  'XPF',
])

/** Convert a Shopify major-unit price (string/number) to integer minor units. */
function toMinorUnits(major: string | number | undefined, currency: string): number {
  const n = typeof major === 'number' ? major : Number.parseFloat(String(major ?? '0'))
  if (Number.isNaN(n)) return 0
  return ZERO_DECIMAL.has(currency.toUpperCase()) ? Math.round(n) : Math.round(n * 100)
}

/**
 * Verify Shopify's `X-Shopify-Hmac-Sha256` header (base64 HMAC-SHA256 of the raw
 * body) using a timing-safe comparison. Returns false on any mismatch or missing
 * input.
 */
export function verifyShopifyHmac(rawBody: string | Buffer, headerHmac: string | undefined, secret: string): boolean {
  if (!headerHmac || !secret) return false
  const digest = crypto.createHmac('sha256', secret).update(rawBody).digest('base64')
  const expected = Buffer.from(digest)
  const actual = Buffer.from(headerHmac)
  if (expected.length !== actual.length) return false
  return crypto.timingSafeEqual(expected, actual)
}

/** Map Shopify financial_status to the contract Order status enum. */
const STATUS_MAP: Record<string, string> = {
  paid: 'paid',
  pending: 'pending',
  authorized: 'pending',
  partially_paid: 'pending',
  refunded: 'refunded',
  partially_refunded: 'paid',
  voided: 'cancelled',
}

interface ShopifyLineItem {
  sku?: string
  quantity?: number
  price?: string | number
}

interface ShopifyOrderPayload {
  id?: string | number
  financial_status?: string
  currency?: string
  total_price?: string | number
  created_at?: string
  line_items?: ShopifyLineItem[]
}

/** Map a Shopify order webhook payload to the shared `Order` contract shape. */
export function mapShopifyOrder(payload: ShopifyOrderPayload): Order {
  const currency = String(payload.currency ?? 'JPY')
  const items: OrderItem[] = Array.isArray(payload.line_items)
    ? payload.line_items.map((li) => ({
        sku: String(li.sku ?? ''),
        quantity: Number(li.quantity ?? 1),
        unitPrice: { amount: toMinorUnits(li.price, currency), currency },
      }))
    : []

  return {
    id: payload.id == null ? '' : String(payload.id),
    status: STATUS_MAP[String(payload.financial_status ?? 'pending')] ?? 'pending',
    items,
    total: { amount: toMinorUnits(payload.total_price, currency), currency },
    createdAt: String(payload.created_at ?? ''),
  }
}
