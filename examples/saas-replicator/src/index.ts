import { createIIIEngine } from './adapters/iiiEngine'
import { Logger } from './log'
import { registerOrchestrator } from './orchestrator'

const engine = createIIIEngine()
registerOrchestrator(engine)

const logger = new Logger(undefined, 'saas-replicator')
logger.info('SaaS Replicator orchestrator started', {
  mode: process.env.SAAS_PROVIDER_MODE === 'stub' ? 'stub' : 'live',
})
