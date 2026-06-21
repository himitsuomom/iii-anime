import assert from 'node:assert/strict'
import { mkdtemp, readFile, rm } from 'node:fs/promises'
import os from 'node:os'
import path from 'node:path'
import { describe, test } from 'node:test'
import { ClaudeCodeBackend } from './claude-code-backend.js'

// Real end-to-end against the local Claude Code CLI. Costs tokens and needs a
// logged-in Claude Code, so it is opt-in: run with STUDIO_E2E=1.
const E2E = process.env.STUDIO_E2E === '1'

describe('ClaudeCodeBackend (e2e)', { skip: E2E ? false : 'set STUDIO_E2E=1 to run' }, () => {
  test('builds a file into the workdir using Claude Code auth (no API key)', async () => {
    const workdir = await mkdtemp(path.join(os.tmpdir(), 'studio-e2e-'))
    try {
      const backend = new ClaudeCodeBackend({ timeoutMs: 180_000 })
      const out = await backend.run({
        project_id: 'prj_e2e',
        workdir,
        systemPrompt: 'You build small artifacts exactly as instructed, then stop.',
        userPrompt:
          'Create a file named BUILT.txt in the current directory whose entire ' +
          'contents are the single word DONE (no trailing newline). Then stop.',
        maxTurns: 8,
      })
      assert.equal(out.ok, true, out.error ?? 'backend failed')
      const built = await readFile(path.join(workdir, 'BUILT.txt'), 'utf8')
      assert.equal(built.trim(), 'DONE')
    } finally {
      await rm(workdir, { recursive: true, force: true })
    }
  })
})
