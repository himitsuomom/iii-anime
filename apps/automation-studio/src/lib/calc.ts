/** Pure profit math for the resale/物販 calculator (kept separate so it is unit-testable). */

export interface ProfitInput {
  /** Purchase cost per unit (円). */
  cost: number
  /** Selling price per unit (円). */
  sell: number
  /** Quantity sold. */
  qty: number
  /** Marketplace selling fee, as a percentage of the sale price. */
  feePercent: number
  /** Payment processing fee, as a percentage of the sale price. */
  paymentPercent: number
  /** Shipping cost per unit (円). */
  shipping: number
  /** Other cost per unit (円). */
  other: number
}

export interface ProfitResult {
  /** Total fee charged per unit (円). */
  fees: number
  /** Profit per unit (円). */
  unitProfit: number
  /** Profit margin as a fraction of the sale price (0–1). */
  margin: number
  /** Break-even sale price (円); Infinity when fees alone reach/exceed 100%. */
  breakeven: number
  /** Profit across all units (円). */
  totalProfit: number
  /** Revenue across all units (円). */
  totalRevenue: number
}

export function computeProfit(input: ProfitInput): ProfitResult {
  const { cost, sell, qty, feePercent, paymentPercent, shipping, other } = input
  const feeRate = (feePercent + paymentPercent) / 100
  const fees = sell * feeRate
  const unitCost = cost + shipping + other + fees
  const unitProfit = sell - unitCost
  const margin = sell > 0 ? unitProfit / sell : 0
  const breakeven = feeRate < 1 ? (cost + shipping + other) / (1 - feeRate) : Number.POSITIVE_INFINITY
  return {
    fees,
    unitProfit,
    margin,
    breakeven,
    totalProfit: unitProfit * qty,
    totalRevenue: sell * qty,
  }
}
