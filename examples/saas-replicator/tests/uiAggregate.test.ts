import assert from 'node:assert/strict'
import { test } from 'node:test'
import type { ScreenAnalysis } from '../src/logic/artifacts'
import { aggregateScreens } from '../src/logic/uiAggregate'

const screen = (id: string, components: string[], colors: string[], fonts: string[]): ScreenAnalysis => ({
  screen: id,
  components,
  tokens: { colors, fonts, spacing: [8, 16] },
})

test('aggregateScreens dedups components (case-insensitive) and counts occurrences', () => {
  const out = aggregateScreens([
    screen('board', ['Button', 'Card'], ['#fff'], ['Inter']),
    screen('card', ['button', 'List'], ['#FFF', '#000'], ['Inter']),
  ])
  assert.equal(out.screens, 2)
  const button = out.components.find((c) => c.name.toLowerCase() === 'button')
  assert.equal(button?.count, 2) // Button + button merged
  // Most frequent first.
  assert.equal(out.components[0]?.name.toLowerCase(), 'button')
  // Colors deduped case-insensitively; spacing deduped + sorted.
  assert.deepEqual(out.designSystem.colors, ['#000', '#fff'])
  assert.deepEqual(out.designSystem.spacing, [8, 16])
  assert.deepEqual(out.designSystem.fonts, ['Inter'])
})

test('aggregateScreens warns on too many fonts/colors', () => {
  const out = aggregateScreens([
    screen('a', ['X'], ['#1', '#2', '#3', '#4', '#5', '#6', '#7', '#8', '#9'], ['F1', 'F2', 'F3', 'F4']),
  ])
  assert.equal(out.consistency.fontCount, 4)
  assert.ok(out.consistency.warnings.some((w) => w.includes('fonts')))
  assert.ok(out.consistency.warnings.some((w) => w.includes('colors')))
})

test('aggregateScreens handles empty input', () => {
  const out = aggregateScreens([])
  assert.equal(out.screens, 0)
  assert.deepEqual(out.components, [])
  assert.equal(out.consistency.warnings.length, 0)
})
