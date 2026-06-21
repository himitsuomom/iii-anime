// Store backed by iii's state worker (iii.state). Used by the running worker;
// tests use MemoryStore. Typed structurally against the state API so it doesn't
// depend on a specific exported SDK type name.
import type { ProjectState } from '../types.js'
import type { Store } from './store.js'

const SCOPE = 'studio'

export interface StateApi {
  get<T>(input: { scope: string; key: string }): Promise<T | null>
  set<T>(input: { scope: string; key: string; value: T }): Promise<unknown>
  list<T>(input: { scope: string }): Promise<T[]>
}

export class IiiStore implements Store {
  constructor(private state: StateApi) {}

  async get(projectId: string): Promise<ProjectState | null> {
    return (await this.state.get<ProjectState>({ scope: SCOPE, key: projectId })) ?? null
  }

  async set(state: ProjectState): Promise<ProjectState> {
    const next = { ...state, updated_at: new Date().toISOString() }
    await this.state.set({ scope: SCOPE, key: state.project_id, value: next })
    return next
  }

  async update(projectId: string, patch: Partial<ProjectState>): Promise<ProjectState> {
    const cur = await this.get(projectId)
    if (!cur) throw new Error(`unknown project: ${projectId}`)
    const next = { ...cur, ...patch, updated_at: new Date().toISOString() }
    await this.state.set({ scope: SCOPE, key: projectId, value: next })
    return next
  }

  async list(): Promise<ProjectState[]> {
    return await this.state.list<ProjectState>({ scope: SCOPE })
  }
}
