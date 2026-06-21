import type { AppTypeAdapter } from './adapter.js'

// Static website: index.html plus optional style.css / app.js, no build step.
// QA asserts the entry page exists and runs a stdlib test that reads the files.
export const staticWeb: AppTypeAdapter = {
  id: 'static-web',
  title: 'Static website (HTML/CSS/JS, no build)',
  designGuidance:
    'A static site: index.html at the root plus optional style.css and app.js. No build step and ' +
    'no dependencies. build_cmd MUST be "true". test_cmd MUST be "node --test" over a *.test.js ' +
    'that reads index.html with node:fs and asserts the required content/structure.',
  rubric: (plan) => ({
    hard: [
      { id: 'index', cmd: 'test -f index.html', expect: 'exit0' },
      { id: 'test', cmd: plan.test_cmd, expect: 'exit0' },
    ],
  }),
}
