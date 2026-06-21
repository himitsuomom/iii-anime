// Select the brain by env: STUDIO_BRAIN=claude (default, local Claude Code) |
// ollama (local Ollama model — no API key, no cost).
import type { Brain } from './brain.js'
import { ClaudeCliBrain } from './claude-cli-brain.js'
import { OllamaBrain } from './ollama-brain.js'

export function brainFromEnv(): Brain {
  switch (process.env.STUDIO_BRAIN ?? 'claude') {
    case 'ollama':
      return new OllamaBrain()
    default:
      return new ClaudeCliBrain()
  }
}
