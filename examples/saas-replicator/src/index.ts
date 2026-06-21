import { Logger } from './log'
import './provider'
import './swarm'
import './director'

const logger = new Logger(undefined, 'saas-replicator')
logger.info('SaaS Replicator orchestrator started', {
  mode: process.env.SAAS_PROVIDER_MODE === 'stub' ? 'stub' : 'live',
})
