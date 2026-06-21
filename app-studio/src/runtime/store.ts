// app-studio project state store: KvStore<ProjectState> from studio-core. The
// generic store holds the mechanism; this file binds it to the software domain.
import { MemoryKvStore, type KvStore } from '../../../studio-core/src/store.js'
import type { ProjectState } from '../types.js'

export type Store = KvStore<ProjectState>

export class MemoryStore extends MemoryKvStore<ProjectState> {
  constructor() {
    super(
      (s) => s.project_id,
      (s) => ({ ...s, updated_at: new Date().toISOString() }),
    )
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
