import assert from 'node:assert/strict'
import { describe, test } from 'node:test'
import { detectAlerts, type AlertItem } from './alerts.js'

const at = (minsAgo: number) => new Date(Date.now() - minsAgo * 60_000).toISOString()

describe('detectAlerts', () => {
  test('flags non-terminal projects idle beyond the threshold', () => {
    const items: AlertItem[] = [
      { project_id: 'a', status: 'building', updated_at: at(20) }, // stuck
      { project_id: 'b', status: 'building', updated_at: at(1) }, // fresh
      { project_id: 'c', status: 'delivered', updated_at: at(99) }, // terminal, ignored
    ]
    const r = detectAlerts(items, { stuckMs: 10 * 60_000 })
    assert.deepEqual(r.stuck, ['a'])
    assert.match(r.alerts.join('\n'), /1 project\(s\) stuck/)
  })

  test('raises a failure spike when most finished projects failed', () => {
    const items: AlertItem[] = [
      { project_id: '1', status: 'failed', updated_at: at(5) },
      { project_id: '2', status: 'failed', updated_at: at(5) },
      { project_id: '3', status: 'failed', updated_at: at(5) },
      { project_id: '4', status: 'delivered', updated_at: at(5) },
    ]
    const r = detectAlerts(items)
    assert.equal(r.failed, 3)
    assert.equal(r.delivered, 1)
    assert.equal(r.failure_spike, true)
    assert.match(r.alerts.join('\n'), /failure spike/)
  })

  test('no alerts on a healthy fleet', () => {
    const items: AlertItem[] = [
      { project_id: '1', status: 'delivered', updated_at: at(5) },
      { project_id: '2', status: 'building', updated_at: at(1) },
    ]
    const r = detectAlerts(items)
    assert.equal(r.failure_spike, false)
    assert.deepEqual(r.alerts, [])
  })
})
