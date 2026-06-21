// Wiki knowledge retrieval: pick prior app docs relevant to a new build so the
// build agent can reuse patterns. Lightweight keyword overlap (no embeddings).
import type { WikiPage } from './wiki-store.js'

const STOP = new Set([
  'the', 'and', 'for', 'with', 'that', 'this', 'app', 'application', 'web', 'page',
  'node', 'using', 'use', 'returns', 'return', 'simple', 'small', 'tiny', 'create',
  'build', 'tests', 'test', 'feature', 'features', 'should', 'http',
])

function tokenize(s: string): string[] {
  return (s.toLowerCase().match(/[a-z0-9]+/g) ?? []).filter((t) => t.length > 2 && !STOP.has(t))
}

/** Pages ranked by keyword overlap with the query (best first); score 0 dropped. */
export function selectRelevantPages(pages: WikiPage[], query: string, limit = 3): WikiPage[] {
  const terms = new Set(tokenize(query))
  if (terms.size === 0) return []
  const scored = pages
    .map((p) => ({ p, score: overlap(p, terms) }))
    .filter((x) => x.score > 0)
    .sort((a, b) => b.score - a.score || (a.p.updated_at < b.p.updated_at ? 1 : -1))
  return scored.slice(0, limit).map((x) => x.p)
}

function overlap(p: WikiPage, terms: Set<string>): number {
  const hay = new Set(tokenize(`${p.title} ${p.content}`))
  let n = 0
  for (const t of terms) if (hay.has(t)) n++
  return n
}

/** Render selected pages as a compact "prior work" section for a build prompt. */
export function renderWikiContext(pages: WikiPage[]): string {
  if (pages.length === 0) return ''
  return (
    'Related prior work from the studio wiki — reuse proven patterns where they fit, ' +
    'but follow THIS spec/plan:\n\n' +
    pages.map((p) => `### ${p.title} (${p.slug})\n${excerpt(p.content)}`).join('\n\n')
  )
}

function excerpt(s: string, n = 800): string {
  return s.length > n ? `${s.slice(0, n)}…` : s
}
