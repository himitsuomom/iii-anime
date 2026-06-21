// LLM wiki: generate a documentation page for a delivered artifact, and answer
// natural-language questions grounded in the accumulated pages. Domain-agnostic:
// the factory renders `body` from its own state and passes a WikiSource.
import type { Brain } from '../brain.js'
import { slugForProject, type WikiPage, type WikiStore } from './wiki-store.js'

const PAGE_SYSTEM =
  'You write a concise developer wiki page in GitHub-flavored Markdown for a delivered ' +
  'artifact. Sections: # <title>, ## Overview, ## Features, ## How it works, ## Run it, ' +
  '## Files. Be accurate to the context given; do not invent capabilities.'

export interface WikiSource {
  /** Id of the producing project (used for the slug + provenance). */
  project_id: string
  title: string
  /** Pre-rendered context (spec/plan/files/run command) the doc is written from. */
  body: string
}

/** Generate a wiki page from a factory-rendered source. */
export async function generateWikiPage(brain: Brain, src: WikiSource): Promise<WikiPage> {
  const content = await brain.text({
    system: PAGE_SYSTEM,
    user: `${src.body}\n\nWrite the wiki page now.`,
    maxTurns: 2,
  })
  const now = new Date().toISOString()
  return {
    slug: slugForProject(src.project_id),
    title: src.title,
    content,
    source_project_id: src.project_id,
    created_at: now,
    updated_at: now,
  }
}

export interface WikiAnswer {
  answer: string
  sources: string[]
}

const ASK_SYSTEM =
  'You answer questions about a catalog of applications using ONLY the wiki pages provided. ' +
  'If the answer is not in the pages, say so. Cite the page slugs you used in brackets, e.g. [app-123].'

/** Answer a question grounded in the wiki pages. */
export async function askWiki(
  brain: Brain,
  store: WikiStore,
  question: string,
): Promise<WikiAnswer> {
  const pages = await store.list()
  if (pages.length === 0) {
    return { answer: 'The wiki is empty — no apps have been documented yet.', sources: [] }
  }
  const context = pages
    .map((p) => `--- page: ${p.slug} (${p.title}) ---\n${cap(p.content)}`)
    .join('\n\n')
  const answer = await brain.text({
    system: ASK_SYSTEM,
    user: `Wiki pages:\n\n${context}\n\n---\nQuestion: ${question}`,
    maxTurns: 2,
  })
  const sources = pages.map((p) => p.slug).filter((slug) => answer.includes(slug))
  return { answer, sources }
}

function cap(s: string, n = 4000): string {
  return s.length > n ? `${s.slice(0, n)}…` : s
}
