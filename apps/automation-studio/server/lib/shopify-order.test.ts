import crypto from 'node:crypto'
import { describe, expect, it } from 'vitest'
import { mapShopifyOrder, verifyShopifyHmac } from './shopify-order.ts'

describe('verifyShopifyHmac', () => {
  const secret = 'shhh-secret'
  const body = JSON.stringify({ id: 1, total_price: '12.00' })
  const goodSig = crypto.createHmac('sha256', secret).update(body).digest('base64')

  it('accepts a correct signature', () => {
    expect(verifyShopifyHmac(body, goodSig, secret)).toBe(true)
  })

  it('rejects a tampered body', () => {
    expect(verifyShopifyHmac(`${body} `, goodSig, secret)).toBe(false)
  })

  it('rejects a wrong secret', () => {
    expect(verifyShopifyHmac(body, goodSig, 'other')).toBe(false)
  })

  it('rejects missing signature or secret', () => {
    expect(verifyShopifyHmac(body, undefined, secret)).toBe(false)
    expect(verifyShopifyHmac(body, goodSig, '')).toBe(false)
  })
})

describe('mapShopifyOrder', () => {
  it('maps a JPY (zero-decimal) order to minor units = major units', () => {
    const order = mapShopifyOrder({
      id: 1234,
      financial_status: 'paid',
      currency: 'JPY',
      total_price: '1200',
      created_at: '2026-06-26T00:00:00Z',
      line_items: [{ sku: 'MUG-1', quantity: 2, price: '600' }],
    })
    expect(order.id).toBe('1234')
    expect(order.status).toBe('paid')
    expect(order.total).toEqual({ amount: 1200, currency: 'JPY' })
    expect(order.items[0]).toEqual({ sku: 'MUG-1', quantity: 2, unitPrice: { amount: 600, currency: 'JPY' } })
  })

  it('converts a 2-decimal currency (USD) to minor units', () => {
    const order = mapShopifyOrder({ id: 9, currency: 'USD', total_price: '12.34', financial_status: 'pending' })
    expect(order.total).toEqual({ amount: 1234, currency: 'USD' })
    expect(order.status).toBe('pending')
  })

  it('maps voided → cancelled and tolerates missing fields', () => {
    const order = mapShopifyOrder({ id: 7, financial_status: 'voided' })
    expect(order.status).toBe('cancelled')
    expect(order.items).toEqual([])
    expect(order.total.amount).toBe(0)
  })
})
