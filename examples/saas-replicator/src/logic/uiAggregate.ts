/**
 * Pure Phase 1 aggregation (no iii-sdk imports — unit-testable).
 *
 * Per-screen `ScreenAnalysis` results are noisy and overlapping. This folds
 * them into one `UiInsights`: a deduped component catalog (with occurrence
 * counts), a merged design system (unique colors/fonts, sorted spacing), and a
 * consistency report that flags likely design drift across screens.
 */

import type { ScreenAnalysis } from './artifacts'

export interface ComponentCount {
  name: string
  count: number
}

export interface UiInsights {
  screens: number
  /** Deduped components across all screens, most frequent first. */
  components: ComponentCount[]
  designSystem: {
    colors: string[]
    fonts: string[]
    spacing: number[]
  }
  consistency: {
    colorCount: number
    fontCount: number
    /** Human-readable warnings about probable inconsistency. */
    warnings: string[]
  }
}

/** Heuristic thresholds for flagging design drift. */
const MAX_FONTS = 3
const MAX_COLORS = 8

export function aggregateScreens(analyses: ScreenAnalysis[]): UiInsights {
  const componentCounts = new Map<string, { name: string; count: number }>()
  const colors = new Set<string>()
  const fonts = new Set<string>()
  const spacing = new Set<number>()

  for (const a of analyses) {
    for (const c of a.components ?? []) {
      const key = c.trim().toLowerCase()
      if (!key) continue
      const existing = componentCounts.get(key)
      if (existing) existing.count++
      else componentCounts.set(key, { name: c.trim(), count: 1 })
    }
    for (const color of a.tokens?.colors ?? []) colors.add(color.trim().toLowerCase())
    for (const font of a.tokens?.fonts ?? []) fonts.add(font.trim())
    for (const s of a.tokens?.spacing ?? []) spacing.add(s)
  }

  const components = [...componentCounts.values()].sort((a, b) => b.count - a.count || a.name.localeCompare(b.name))
  const designSystem = {
    colors: [...colors].sort(),
    fonts: [...fonts].sort(),
    spacing: [...spacing].sort((a, b) => a - b),
  }

  const warnings: string[] = []
  if (designSystem.fonts.length > MAX_FONTS) {
    warnings.push(`${designSystem.fonts.length} distinct fonts (> ${MAX_FONTS}); consolidate the type scale`)
  }
  if (designSystem.colors.length > MAX_COLORS) {
    warnings.push(`${designSystem.colors.length} distinct colors (> ${MAX_COLORS}); define a smaller palette`)
  }

  return {
    screens: analyses.length,
    components,
    designSystem,
    consistency: { colorCount: designSystem.colors.length, fontCount: designSystem.fonts.length, warnings },
  }
}
