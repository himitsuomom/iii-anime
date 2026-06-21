import assert from 'node:assert/strict'
import { describe, test } from 'node:test'
import type { FetchLike } from './ollama-brain.js'
import { OllamaBrain } from './ollama-brain.js'

// Fake Ollama HTTP: records the request body, returns a canned chat response.
function fakeOllama(content: string): { fetchFn: FetchLike; lastBody: () => unknown } {
  let body: unknown
  const fetchFn: FetchLike = async (_url, init) => {
    body = JSON.parse(init?.body ?? '{}')
    return {
      ok: true,
      status: 200,
      async text() {
        return JSON.stringify({ message: { role: 'assistant', content } })
      },
    }
  }
  return { fetchFn, lastBody: () => body }
}

describe('OllamaBrain', () => {
  test('json() requests JSON mode, parses + validates', async () => {
    const f = fakeOllama('{"goal":"x","items":["a"]}')
    const brain = new OllamaBrain({ model: 'qwen2.5-coder:1.5b', fetchFn: f.fetchFn })
    const out = await brain.json({
      system: 'sys',
      user: 'make json',
      validate: (u) => u as { goal: string; items: string[] },
    })
    assert.deepEqual(out, { goal: 'x', items: ['a'] })
    const body = f.lastBody() as { model: string; format?: string; messages: unknown[] }
    assert.equal(body.model, 'qwen2.5-coder:1.5b')
    assert.equal(body.format, 'json') // json() asks Ollama for JSON output
    assert.equal((body.messages as { role: string }[])[0]?.role, 'system')
  })

  test('json() strips code fences before parsing', async () => {
    const f = fakeOllama('```json\n{"ok":true}\n```')
    const brain = new OllamaBrain({ fetchFn: f.fetchFn })
    const out = await brain.json({ system: '', user: '', validate: (u) => u as { ok: boolean } })
    assert.deepEqual(out, { ok: true })
  })

  test('text() returns the message content (no json mode)', async () => {
    const f = fakeOllama('# Wiki page\nhello')
    const brain = new OllamaBrain({ fetchFn: f.fetchFn })
    const out = await brain.text({ system: 's', user: 'write' })
    assert.match(out, /Wiki page/)
    assert.equal((f.lastBody() as { format?: string }).format, undefined) // no json mode for text
  })

  test('non-2xx surfaces an error', async () => {
    const fetchFn: FetchLike = async () => ({ ok: false, status: 500, async text() { return 'boom' } })
    const brain = new OllamaBrain({ fetchFn })
    await assert.rejects(() => brain.text({ system: '', user: '' }), /ollama 500/)
  })
})
