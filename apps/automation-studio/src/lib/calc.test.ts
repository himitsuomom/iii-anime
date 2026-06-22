import { describe, expect, it } from 'vitest'
import { computeProfit } from './calc.ts'

describe('computeProfit', () => {
  it('computes fees, profit, margin and totals', () => {
    const r = computeProfit({
      cost: 1000,
      sell: 2500,
      qty: 10,
      feePercent: 10,
      paymentPercent: 3.6,
      shipping: 300,
      other: 0,
    })
    expect(r.fees).toBeCloseTo(340, 5) // 2500 * 0.136
    expect(r.unitProfit).toBeCloseTo(860, 5) // 2500 - 1000 - 300 - 340
    expect(r.margin).toBeCloseTo(0.344, 5)
    expect(r.totalProfit).toBeCloseTo(8600, 5)
    expect(r.totalRevenue).toBe(25000)
  })

  it('computes the break-even sale price', () => {
    const r = computeProfit({
      cost: 1000,
      sell: 2500,
      qty: 1,
      feePercent: 10,
      paymentPercent: 3.6,
      shipping: 300,
      other: 0,
    })
    // (1000 + 300) / (1 - 0.136)
    expect(r.breakeven).toBeCloseTo(1504.63, 1)
  })

  it('returns Infinity break-even when fees reach 100%', () => {
    const r = computeProfit({
      cost: 1000,
      sell: 2000,
      qty: 1,
      feePercent: 60,
      paymentPercent: 40,
      shipping: 0,
      other: 0,
    })
    expect(r.breakeven).toBe(Number.POSITIVE_INFINITY)
  })

  it('reports a negative profit when costs exceed the sale price', () => {
    const r = computeProfit({
      cost: 2000,
      sell: 1500,
      qty: 3,
      feePercent: 10,
      paymentPercent: 0,
      shipping: 200,
      other: 0,
    })
    expect(r.unitProfit).toBeLessThan(0)
    expect(r.totalProfit).toBeLessThan(0)
  })

  it('avoids division by zero when the sale price is 0', () => {
    const r = computeProfit({
      cost: 0,
      sell: 0,
      qty: 1,
      feePercent: 10,
      paymentPercent: 0,
      shipping: 0,
      other: 0,
    })
    expect(r.margin).toBe(0)
  })
})
