import { describe, expect, it } from 'vitest'
import { getMetrics, recordDescription, recordInquiry } from './metrics.ts'

describe('runtime metrics', () => {
  it('counts descriptions and inquiries monotonically', () => {
    const before = getMetrics()
    recordDescription()
    recordDescription()
    recordInquiry()
    const after = getMetrics()
    expect(after.descriptionsGenerated).toBe(before.descriptionsGenerated + 2)
    expect(after.inquiriesAnswered).toBe(before.inquiriesAnswered + 1)
  })

  it('returns a copy (callers cannot mutate internal state)', () => {
    const snap = getMetrics()
    snap.descriptionsGenerated = 9999
    expect(getMetrics().descriptionsGenerated).not.toBe(9999)
  })
})
