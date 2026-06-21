// Store backed by iii's state worker. State ops are invoked as engine functions
// (`state::get` / `state::set` / `state::list`) via iii.trigger — there is no
// `iii.state` accessor on ISdk. Used by the running worker; tests use MemoryStore.
import type { TriggerFn } from '../../../studio-core/src/iii.js'
import type { ProjectState } from '../types.js'
import type { Store } from './store.js'

export type { TriggerFn }

const SCOPE = 'studio'

export class IiiStore implements Store {
  constructor(private iii: TriggerFn) {}

  async get(projectId: string): Promise<ProjectState | null> {
    const v = await this.iii.trigger<{ scope: string; key: string }, ProjectState | null>({
      function_id: 'state::get',
      payload: { scope: SCOPE, key: projectId },
    })
    return v ?? null
  }

  async set(state: ProjectState): Promise<ProjectState> {
    // Full replace — store as given (caller controls updated_at). update() stamps.
    await this.iii.trigger<{ scope: string; key: string; value: ProjectState }, unknown>({
      function_id: 'state::set',
      payload: { scope: SCOPE, key: state.project_id, value: state },
    })
    return state
  }

  async update(projectId: string, patch: Partial<ProjectState>): Promise<ProjectState> {
    const cur = await this.get(projectId)
    if (!cur) throw new Error(`unknown project: ${projectId}`)
    const next = { ...cur, ...patch, updated_at: new Date().toISOString() }
    await this.iii.trigger<{ scope: string; key: string; value: ProjectState }, unknown>({
      function_id: 'state::set',
      payload: { scope: SCOPE, key: projectId, value: next },
    })
    return next
  }

  async list(): Promise<ProjectState[]> {
    const v = await this.iii.trigger<{ scope: string }, ProjectState[]>({
      function_id: 'state::list',
      payload: { scope: SCOPE },
    })
    return v ?? []
  }
}
