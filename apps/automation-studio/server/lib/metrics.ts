/**
 * In-process runtime metrics surfaced on the dashboard. These are real counts
 * of work this server instance has done (not mock figures): how many product
 * descriptions were generated and how many customer inquiries were answered,
 * across both the HTTP routes and the iii worker functions.
 */
export interface RuntimeMetrics {
  descriptionsGenerated: number
  inquiriesAnswered: number
}

const metrics: RuntimeMetrics = {
  descriptionsGenerated: 0,
  inquiriesAnswered: 0,
}

export function recordDescription(): void {
  metrics.descriptionsGenerated += 1
}

export function recordInquiry(): void {
  metrics.inquiriesAnswered += 1
}

export function getMetrics(): RuntimeMetrics {
  return { ...metrics }
}
