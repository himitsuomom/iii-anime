// Client for the app-studio worker's HTTP routes. The studio registers routes
// at the engine root (/projects, /wiki, ...). When the console is served from
// the same origin as the studio engine this works as-is; otherwise point it at
// the studio with VITE_STUDIO_BASE (e.g. "http://localhost:3111").
const BASE = (import.meta.env.VITE_STUDIO_BASE as string | undefined) ?? ''

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, init)
  const text = await res.text()
  const data = text ? JSON.parse(text) : null
  // Studio root routes return the body directly (HTTP status carries the code).
  if (data && typeof data === 'object' && 'status_code' in data && 'body' in data) {
    return (data as { body: T }).body
  }
  return data as T
}

export interface ProjectSummary {
  project_id: string
  status: string
  iteration: number
  goal?: string
  app_type?: string
  passed?: boolean
  updated_at: string
}

export interface ProjectDetail extends ProjectSummary {
  idea: string
  plan?: { app_type: string; stack: string[]; test_cmd: string; run_cmd?: string }
  last_qa?: { passed: boolean; failures: string[]; score: number }
  artifacts?: { files: string[]; preview_cmd?: string }
}

export interface WikiPageSummary {
  slug: string
  title: string
  source_project_id?: string
  updated_at: string
}

export const listProjects = () => call<{ projects: ProjectSummary[] }>('/projects')
export const getProject = (id: string) => call<ProjectDetail>(`/projects/${id}`)
export const createProject = (idea: string, require_approval: boolean) =>
  call<{ project_id: string }>('/projects', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ idea, require_approval }),
  })
export const approveProject = (id: string) => call(`/projects/${id}/approve`, { method: 'POST' })
export const rejectProject = (id: string) => call(`/projects/${id}/reject`, { method: 'POST' })
export const listWiki = () => call<{ pages: WikiPageSummary[] }>('/wiki')
export const askWiki = (question: string) =>
  call<{ answer: string; sources: string[] }>('/wiki/ask', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ question }),
  })
