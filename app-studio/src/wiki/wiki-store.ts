// Wiki page storage. The studio auto-documents every delivered app into a wiki
// page; pages accumulate as a knowledge base you can browse and query.
export interface WikiPage {
  slug: string
  title: string
  content: string // markdown
  source_project_id?: string
  created_at: string
  updated_at: string
}

export interface WikiStore {
  get(slug: string): Promise<WikiPage | null>
  put(page: WikiPage): Promise<WikiPage>
  list(): Promise<WikiPage[]>
}

export class MemoryWikiStore implements WikiStore {
  private map = new Map<string, WikiPage>()
  async get(slug: string): Promise<WikiPage | null> {
    return this.map.get(slug) ?? null
  }
  async put(page: WikiPage): Promise<WikiPage> {
    this.map.set(page.slug, page)
    return page
  }
  async list(): Promise<WikiPage[]> {
    return [...this.map.values()]
  }
}

/** Filesystem/derived slug for a project's wiki page. */
export function slugForProject(projectId: string): string {
  return projectId.replace(/^prj_/, 'app-')
}
