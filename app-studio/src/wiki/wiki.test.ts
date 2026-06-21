import assert from 'node:assert/strict'
import { describe, test } from 'node:test'
import type { Brain, JsonRequest, TextRequest } from '../brain/brain.js'
import type { ProjectState } from '../types.js'
import { askWiki, generateWikiPage } from './wiki.js'
import { MemoryWikiStore } from './wiki-store.js'

class FakeBrain implements Brain {
  readonly id = 'fake'
  lastText?: TextRequest
  constructor(private reply: (req: TextRequest) => string) {}
  async json<T>(req: JsonRequest<T>): Promise<T> {
    return req.validate({})
  }
  async text(req: TextRequest): Promise<string> {
    this.lastText = req
    return this.reply(req)
  }
}

const project = (over: Partial<ProjectState> = {}): ProjectState => ({
  project_id: 'prj_abc',
  idea: 'a health endpoint',
  status: 'delivered',
  iteration: 1,
  max_iterations: 5,
  workdir: '/w',
  spec: { goal: 'Health endpoint', features: ['/health'], acceptance: ['200'], assumptions: [] },
  plan: { app_type: 'web-node', stack: ['node'], tasks: [], build_cmd: 'true', test_cmd: 'node --test' },
  artifacts: { files: ['server.js', 'test.js'], preview_cmd: 'node server.js' },
  updated_at: new Date().toISOString(),
  ...over,
})

describe('wiki page generation', () => {
  test('produces a page with slug/title and includes project context in the prompt', async () => {
    const brain = new FakeBrain(() => '# Health endpoint\n## Overview\n...')
    const page = await generateWikiPage(brain, project())
    assert.equal(page.slug, 'app-abc')
    assert.equal(page.title, 'Health endpoint')
    assert.equal(page.source_project_id, 'prj_abc')
    assert.match(page.content, /Overview/)
    // The generation prompt must carry the files + plan so the doc is accurate.
    assert.match(brain.lastText!.user, /server\.js/)
    assert.match(brain.lastText!.user, /node --test/)
  })
})

describe('wiki ask', () => {
  test('empty wiki returns a clear message without calling the brain', async () => {
    let called = false
    const brain = new FakeBrain(() => {
      called = true
      return 'x'
    })
    const res = await askWiki(brain, new MemoryWikiStore(), 'what apps exist?')
    assert.match(res.answer, /empty/i)
    assert.equal(called, false)
    assert.deepEqual(res.sources, [])
  })

  test('grounds the answer in stored pages and reports cited sources', async () => {
    const store = new MemoryWikiStore()
    await store.put({
      slug: 'app-abc',
      title: 'Health endpoint',
      content: 'A server with GET /health returning {status:ok}.',
      created_at: 'now',
      updated_at: 'now',
    })
    const brain = new FakeBrain((req) => {
      // Answer must have been given the page content as context.
      assert.match(req.user, /GET \/health/)
      return 'The health app exposes GET /health [app-abc].'
    })
    const res = await askWiki(brain, store, 'is there a health endpoint?')
    assert.match(res.answer, /health/)
    assert.deepEqual(res.sources, ['app-abc'])
  })
})
