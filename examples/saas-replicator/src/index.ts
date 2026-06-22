import { createIIIEngine } from './adapters/iiiEngine'
import { Logger } from './log'
import { withObservability } from './observability'
import { registerOrchestrator } from './orchestrator'
import { logPreflight, runPreflight } from './preflight'

// Wrap the bus with app-level tracing + token-budget enforcement (DESIGN §12).
const engine = withObservability(createIIIEngine())
registerOrchestrator(engine)

const logger = new Logger(undefined, 'saas-replicator')
logger.info('SaaS Replicator orchestrator started', {
  mode: process.env.SAAS_PROVIDER_MODE === 'stub' ? 'stub' : 'live',
  tokenBudget: engine.telemetry.budgetLimit || 'unlimited',
})

// Validate the runtime configuration once the bus is connected.
runPreflight(engine).then(logPreflight)
