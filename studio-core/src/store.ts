// Generic key-value store for factory project state. Domain-agnostic: a factory
// supplies the key extractor (and an optional stamp applied on update, e.g. to
// touch updated_at). app-studio's Store is KvStore<ProjectState>; another
// factory parameterizes it with its own state type.

export interface KvStore<T> {
  get(id: string): Promise<T | null>
  /** Full replace — stored as given (caller controls timestamps). */
  set(value: T): Promise<T>
  /** Merge patch into the existing value; applies the stamp if configured. */
  update(id: string, patch: Partial<T>): Promise<T>
  list(): Promise<T[]>
}

export class MemoryKvStore<T> implements KvStore<T> {
  private map = new Map<string, T>()

  constructor(
    private keyOf: (value: T) => string,
    /** Applied on update() only (not set()), e.g. to refresh updated_at. */
    private stamp?: (value: T) => T,
  ) {}

  async get(id: string): Promise<T | null> {
    return this.map.get(id) ?? null
  }

  async set(value: T): Promise<T> {
    this.map.set(this.keyOf(value), value)
    return value
  }

  async update(id: string, patch: Partial<T>): Promise<T> {
    const cur = this.map.get(id)
    if (!cur) throw new Error(`unknown key: ${id}`)
    const next = { ...cur, ...patch }
    const stamped = this.stamp ? this.stamp(next) : next
    this.map.set(id, stamped)
    return stamped
  }

  async list(): Promise<T[]> {
    return [...this.map.values()]
  }
}
