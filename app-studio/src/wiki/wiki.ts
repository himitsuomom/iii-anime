// LLM wiki: generate a documentation page for a delivered app, and answer
// natural-language questions grounded in the accumulated pages.
import type { Brain } from '../brain/brain.js'
import type { ProjectState } from '../types.js'
import { slugForProject, type WikiPage, type WikiStore } from './wiki-store.js'

const PAGE_SYSTEM =
  'You write a concise developer wiki page in GitHub-flavored Markdown for a delivered ' +
  'application. Sections: # <title>, ## Overview, ## Features, ## How it works, ## Run it, ' +
  '## Files. Be accurate to the spec/plan/files given; do not invent capabilities.'

/** Generate a wiki page documenting a delivered project. */
export async function generateWikiPage(brain: Brain, project: ProjectState): Promise<WikiPage> {
  const title = project.spec?.goal ?? project.idea
  const user =
    `Project: ${project.project_id}\n\n` +
    `## Specification\n${JSON.stringify(project.spec, null, 2)}\n\n` +
    `## Plan\n${JSON.stringify(project.plan, null, 2)}\n\n` +
    `## Files\n${(project.artifacts?.files ?? []).join('\n')}\n\n` +
    `Run command: ${project.artifacts?.preview_cmd ?? project.plan?.run_cmd ?? '(none)'}\n\n` +
    `Write the wiki page now.`
  const content = await brain.text({ system: PAGE_SYSTEM, user, maxTurns: 2 })
  const now = new Date().toISOString()
  return {
    slug: slugForProject(project.project_id),
    title,
    content,
    source_project_id: project.project_id,
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
