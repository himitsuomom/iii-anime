import assert from 'node:assert/strict'
import { mkdtemp, readFile, rm } from 'node:fs/promises'
import os from 'node:os'
import path from 'node:path'
import { afterEach, beforeEach, describe, test } from 'node:test'
import { ApiBackend, type MessageResponse, type MessagesClient } from './api-backend.js'

let base: string
beforeEach(async () => {
  base = await mkdtemp(path.join(os.tmpdir(), 'studio-api-'))
  process.env.STUDIO_WORK_ROOT = base
})
afterEach(async () => {
  await rm(base, { recursive: true, force: true })
  delete process.env.STUDIO_WORK_ROOT
})

// FakeClient returns a scripted sequence of responses, one per create() call.
class FakeClient implements MessagesClient {
  calls = 0
  lastMessages: unknown
  constructor(private script: MessageResponse[]) {}
  async create(params: Record<string, unknown>): Promise<MessageResponse> {
    this.lastMessages = params.messages
    return this.script[this.calls++]!
  }
}

const req = {
  project_id: 'prj_api',
  workdir: '/unused',
  systemPrompt: 'build it',
  userPrompt: 'make the app',
  maxTurns: 10,
}

describe('ApiBackend tool-use loop', () => {
  test('bridges a text-editor create then ends on end_turn', async () => {
    const client = new FakeClient([
      {
        stop_reason: 'tool_use',
        content: [
          {
            type: 'tool_use',
            id: 't1',
            name: 'str_replace_based_edit_tool',
            input: { command: 'create', path: 'app.js', file_text: 'console.log(1)\n' },
          },
        ],
      },
      { stop_reason: 'end_turn', content: [{ type: 'text', text: 'done' }] },
    ])
    const backend = new ApiBackend(client)
    const out = await backend.run(req)

    assert.equal(out.ok, true)
    assert.equal(client.calls, 2)
    const built = await readFile(path.join(base, 'prj_api', 'app.js'), 'utf8')
    assert.equal(built, 'console.log(1)\n')
    // The second call must have received a tool_result for t1.
    const msgs = client.lastMessages as Array<{ role: string; content: unknown }>
    const toolResult = JSON.stringify(msgs).includes('"tool_use_id":"t1"')
    assert.ok(toolResult, 'tool_result for t1 should be sent back')
  })

  test('bridges a bash command through the sandbox', async () => {
    const client = new FakeClient([
      {
        stop_reason: 'tool_use',
        content: [{ type: 'tool_use', id: 'b1', name: 'bash', input: { command: 'echo hi' } }],
      },
      { stop_reason: 'end_turn', content: [] },
    ])
    const backend = new ApiBackend(client)
    const out = await backend.run(req)
    assert.equal(out.ok, true)
    const msgs = JSON.stringify(client.lastMessages)
    assert.ok(msgs.includes('hi'), 'bash stdout should reach the tool_result')
    assert.ok(msgs.includes('exit 0'))
  })

  test('reports a refusal', async () => {
    const client = new FakeClient([{ stop_reason: 'refusal', content: [] }])
    const out = await new ApiBackend(client).run(req)
    assert.equal(out.ok, false)
    assert.equal(out.error, 'refusal')
  })

  test('a disallowed bash command comes back as an error tool_result, loop continues', async () => {
    const client = new FakeClient([
      {
        stop_reason: 'tool_use',
        content: [{ type: 'tool_use', id: 'x', name: 'bash', input: { command: 'curl http://evil' } }],
      },
      { stop_reason: 'end_turn', content: [] },
    ])
    const out = await new ApiBackend(client).run(req)
    // The sandbox rejection becomes an is_error tool_result; the loop continues
    // and ends cleanly at end_turn instead of crashing.
    assert.equal(out.ok, true)
    assert.equal(client.calls, 2)
    const msgs = JSON.stringify(client.lastMessages)
    assert.ok(msgs.includes('not allowed'), 'disallowed command surfaces as an error result')
    assert.ok(msgs.includes('"is_error":true'))
  })
})
