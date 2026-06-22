/**
 * Pure deploy-plan construction (no iii-sdk / node imports — unit-testable).
 *
 * Derives a build/deploy plan from the generated codebase: the entry point, the
 * file manifest, and the ordered steps a deploy worker (or the local simulator)
 * should run. The wiring in `src/deploy.ts` executes the plan.
 */

import type { Codebase } from './artifacts'

export interface DeployPlan {
  target: string
  entrypoint: string
  files: string[]
  steps: string[]
}

/** Pick the app entry point (src/app.* if present, else the test file). */
function pickEntrypoint(codebase: Codebase): string {
  const app = codebase.files.find((f) => /(^|\/)app\.(mjs|js|cjs)$/i.test(f.path))
  return app?.path ?? codebase.testFile
}

export function buildDeployPlan(codebase: Codebase): DeployPlan {
  const files = codebase.files.map((f) => f.path)
  const entrypoint = pickEntrypoint(codebase)
  const steps = [
    `bundle ${files.length} files`,
    `run test suite (${codebase.testFile})`,
    `package entrypoint ${entrypoint}`,
    'publish to host',
    'register PWA manifest',
  ]
  return { target: codebase.target, entrypoint, files, steps }
}
