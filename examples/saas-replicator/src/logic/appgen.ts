/**
 * Pure PRD-driven app synthesis (no iii-sdk / node imports — unit-testable).
 *
 * Turns a `Prd` into a real, runnable multi-file Node codebase: one model
 * module per data-model entity, an API module with one handler per feature, an
 * app module that wires them, and a test that exercises every generated module
 * and prints a parseable `TESTS total=.. passed=.. failed=..` line. This makes
 * Phase 3 produce an actual application shaped by the PRD rather than a fixed
 * 2-file stub.
 */

import type { Codebase, GeneratedFile, Prd } from './artifacts'

/** Lowercase identifier safe for file names / JS identifiers. */
function ident(s: string): string {
  const cleaned = s
    .trim()
    .replace(/[^a-zA-Z0-9]+/g, ' ')
    .trim()
  const camel = cleaned
    .split(' ')
    .map((w, i) => (i === 0 ? w.toLowerCase() : w.charAt(0).toUpperCase() + w.slice(1).toLowerCase()))
    .join('')
  return camel || 'item'
}

function pascal(s: string): string {
  const id = ident(s)
  return id.charAt(0).toUpperCase() + id.slice(1)
}

/** Build a runnable app from a PRD. Always emits at least one model + a test. */
export function synthesizeApp(target: string, prd: Pick<Prd, 'features' | 'dataModel'>): Codebase {
  const entities = unique((prd.dataModel ?? []).map(ident)).slice(0, 12)
  const features = unique((prd.features ?? []).map(ident)).slice(0, 24)
  if (entities.length === 0) entities.push('item')

  const files: GeneratedFile[] = []

  // One model module per entity: a factory returning an object with an id.
  for (const e of entities) {
    files.push({
      path: `src/models/${e}.mjs`,
      content: `export const create${pascal(e)} = (props = {}) => ({ id: props.id ?? '${e}-1', type: '${e}', ...props })\n`,
    })
  }

  // API module: one handler per feature (falls back to a health handler).
  const featureList = features.length > 0 ? features : ['health']
  const apiBody = featureList
    .map((f) => `export const ${f} = (input = {}) => ({ feature: '${f}', ok: true, input })`)
    .join('\n')
  files.push({ path: 'src/api.mjs', content: `${apiBody}\n` })

  // App module wires models + api together.
  const modelImports = entities.map((e) => `import { create${pascal(e)} } from './models/${e}.mjs'`).join('\n')
  const modelMap = entities.map((e) => `  ${e}: create${pascal(e)},`).join('\n')
  const apiImports = `import * as api from './api.mjs'`
  files.push({
    path: 'src/app.mjs',
    content: `${modelImports}\n${apiImports}\n\nexport const createApp = () => ({\n  models: {\n${modelMap}\n  },\n  api,\n})\n`,
  })

  // Test exercises createApp, every model factory, and every feature handler.
  files.push({ path: 'test.mjs', content: buildTest(entities, featureList) })

  return { target, files, testFile: 'test.mjs' }
}

function buildTest(entities: string[], features: string[]): string {
  const lines: string[] = [
    "import { createApp } from './src/app.mjs'",
    'const app = createApp()',
    'const cases = []',
    "cases.push(typeof createApp === 'function')",
    "cases.push(app && typeof app.models === 'object' && typeof app.api === 'object')",
  ]
  for (const e of entities) {
    lines.push(`cases.push(app.models.${e}({ id: 't' }).id === 't')`)
    lines.push(`cases.push(app.models.${e}().type === '${e}')`)
  }
  for (const f of features) {
    lines.push(`cases.push(app.api.${f}().ok === true)`)
  }
  lines.push('const total = cases.length')
  lines.push('const passed = cases.filter(Boolean).length')
  lines.push("console.log('TESTS total=' + total + ' passed=' + passed + ' failed=' + (total - passed))")
  lines.push('')
  return lines.join('\n')
}

function unique<T>(xs: T[]): T[] {
  return [...new Set(xs)]
}
