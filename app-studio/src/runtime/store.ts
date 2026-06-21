// Project state store. The pipeline and orchestrator talk to this interface;
// tests use MemoryStore, the iii worker wraps iii.state (see index.ts).
import type { ProjectState } from '../types.js'

export interface Store {
  get(projectId: string): Promise<ProjectState | null>
  set(state: ProjectState): Promise<ProjectState>
  update(projectId: string, patch: Partial<ProjectState>): Promise<ProjectState>
  list(): Promise<ProjectState[]>
}

export class MemoryStore implements Store {
  private map = new Map<string, ProjectState>()

  async get(projectId: string): Promise<ProjectState | null> {
    return this.map.get(projectId) ?? null
  }

  async set(state: ProjectState): Promise<ProjectState> {
    // Full replace — store as given (caller controls updated_at). update() stamps.
    this.map.set(state.project_id, state)
    return state
  }

  async update(projectId: string, patch: Partial<ProjectState>): Promise<ProjectState> {
    const cur = this.map.get(projectId)
    if (!cur) throw new Error(`unknown project: ${projectId}`)
    const next = { ...cur, ...patch, updated_at: new Date().toISOString() }
    this.map.set(projectId, next)
    return next
  }

  async list(): Promise<ProjectState[]> {
    return [...this.map.values()]
  }
}

export function initialProjectState(
  projectId: string,
  idea: string,
  workdir: string,
  maxIterations: number,
): ProjectState {
  return {
    project_id: projectId,
    idea,
    status: 'intake',
    iteration: 0,
    max_iterations: maxIterations,
    workdir,
    updated_at: new Date().toISOString(),
  }
}
