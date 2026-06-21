// A factory descriptor is the namespacing contract that lets multiple AI
// factories coexist on one iii engine without colliding: distinct HTTP route
// prefix, state scope, and build/render queue. A deployment registers each
// factory it runs.

export interface FactoryDescriptor {
  /** Stable id, e.g. "app-studio" / "video-studio". */
  id: string
  title: string
  /** HTTP route prefix, e.g. "" (root) or "/video". */
  routePrefix: string
  /** iii state scope, e.g. "studio" / "video". */
  stateScope: string
  /** Queue name for the heavy stage (build/render). */
  buildQueue: string
}

const registry = new Map<string, FactoryDescriptor>()

export function registerFactory(d: FactoryDescriptor): FactoryDescriptor {
  if (registry.has(d.id)) throw new Error(`factory already registered: ${d.id}`)
  // Guard against namespace collisions across factories.
  for (const other of registry.values()) {
    if (other.routePrefix === d.routePrefix) throw new Error(`route prefix collision: "${d.routePrefix}"`)
    if (other.stateScope === d.stateScope) throw new Error(`state scope collision: "${d.stateScope}"`)
  }
  registry.set(d.id, d)
  return d
}

export function getFactory(id: string): FactoryDescriptor | undefined {
  return registry.get(id)
}

export function listFactories(): FactoryDescriptor[] {
  return [...registry.values()]
}

export function resetFactories(): void {
  registry.clear()
}
