/**
 * Aggregates the real dashboard KPIs from the engine: order stats and inventory
 * alerts, fetched via the EC worker functions (orders::stats / inventory::alerts).
 * Returns an empty object when no worker is connected, so the dashboard degrades
 * gracefully to AI-activity metrics only.
 */
import { getWorker } from '../iii-worker.ts'
import type { Money } from './shopify-order.ts'

export interface DashboardExtras {
  revenue?: Money
  orderCount?: number
  inventoryAlertCount?: number
}

interface OrderStats {
  revenue?: Money
  orderCount?: number
}

interface InventoryAlerts {
  count?: number
}

export async function fetchDashboardExtras(): Promise<DashboardExtras> {
  const worker = getWorker()
  if (!worker) return {}
  try {
    const [stats, alerts] = await Promise.all([
      worker.trigger({ function_id: 'orders::stats', payload: {} }) as Promise<OrderStats>,
      worker.trigger({ function_id: 'inventory::alerts', payload: {} }) as Promise<InventoryAlerts>,
    ])
    return {
      revenue: stats?.revenue,
      orderCount: stats?.orderCount,
      inventoryAlertCount: alerts?.count,
    }
  } catch (err) {
    console.error('dashboard extras fetch failed:', err)
    return {}
  }
}
