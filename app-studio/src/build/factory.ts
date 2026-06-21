// Select the build backend by env. Default is the local Claude Code CLI (no API
// key); set STUDIO_BUILD_BACKEND=api to use the Anthropic Messages API directly
// (needs ANTHROPIC_API_KEY and `@anthropic-ai/sdk` installed).
import type { BuildBackend } from './backend.js'
import { ClaudeCodeBackend } from './claude-code-backend.js'

export async function buildBackendFromEnv(): Promise<BuildBackend> {
  const kind = process.env.STUDIO_BUILD_BACKEND ?? 'claude-code'
  if (kind === 'api') return createApiBackend()
  return new ClaudeCodeBackend()
}

async function createApiBackend(): Promise<BuildBackend> {
  const { ApiBackend } = await import('./api-backend.js')
  // Non-literal specifier so the optional SDK isn't required to typecheck/run
  // the default (Claude Code) path.
  const specifier = '@anthropic-ai/sdk'
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const mod: any = await import(specifier)
  const Anthropic = mod.default ?? mod.Anthropic
  const client = new Anthropic() // reads ANTHROPIC_API_KEY
  return new ApiBackend(
    {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      create: (params: Record<string, unknown>) => client.messages.create(params as any),
    },
    { model: process.env.STUDIO_API_MODEL ?? 'claude-opus-4-8' },
  )
}
