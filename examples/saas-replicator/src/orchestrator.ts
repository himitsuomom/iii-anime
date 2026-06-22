import { registerDirector } from './director'
import type { Engine } from './engine'
import { registerPreflight } from './preflight'
import { registerProvider } from './provider'
import { registerSwarm } from './swarm'

/** Register every orchestrator function onto an engine (real or in-memory). */
export function registerOrchestrator(engine: Engine): void {
  registerProvider(engine)
  registerSwarm(engine)
  registerDirector(engine)
  registerPreflight(engine)
}
