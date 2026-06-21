import type { AppTypeAdapter } from './adapter.js'

// Zero-dependency Node.js app (server, library, or CLI) — the P0 default.
// Stdlib only, no install step; QA runs the plan's build/test commands.
export const webNode: AppTypeAdapter = {
  id: 'web-node',
  title: 'Zero-dependency Node.js app (stdlib only)',
  designGuidance:
    'Use ONLY the Node.js standard library — no npm dependencies, no install step. The app runs ' +
    'with `node` alone. build_cmd is a fast no-op check like "node --check <entry>.js"; test_cmd ' +
    'MUST be "node --test" over *.test.js using node:test + node:assert.',
  rubric: (plan) => ({
    hard: [
      { id: 'build', cmd: plan.build_cmd, expect: 'exit0' },
      { id: 'test', cmd: plan.test_cmd, expect: 'exit0' },
    ],
  }),
}
