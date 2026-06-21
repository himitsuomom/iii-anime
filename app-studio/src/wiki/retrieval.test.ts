import assert from 'node:assert/strict'
import { describe, test } from 'node:test'
import { renderWikiContext, selectRelevantPages } from './retrieval.js'
import type { WikiPage } from './wiki-store.js'

const page = (slug: string, title: string, content: string): WikiPage => ({
  slug,
  title,
  content,
  created_at: 'now',
  updated_at: 'now',
})

describe('selectRelevantPages', () => {
  const pages = [
    page('app-auth', 'JWT auth service', 'Login endpoint issuing JWT tokens and refresh tokens.'),
    page('app-todo', 'Todo list API', 'CRUD endpoints for todo items stored in memory.'),
    page('app-health', 'Health endpoint', 'A server exposing /health returning ok.'),
  ]

  test('ranks by keyword overlap and drops zero-score pages', () => {
    const hits = selectRelevantPages(pages, 'a service that issues JWT tokens for login')
    assert.equal(hits[0]?.slug, 'app-auth')
    // unrelated pages (todo/health) share no meaningful terms -> excluded
    assert.ok(!hits.some((p) => p.slug === 'app-todo'))
  })

  test('respects the limit', () => {
    const hits = selectRelevantPages(pages, 'endpoint server tokens todo health login', 2)
    assert.ok(hits.length <= 2)
  })

  test('empty / stopword-only query returns nothing', () => {
    assert.deepEqual(selectRelevantPages(pages, 'the and a web app'), [])
  })
})

describe('renderWikiContext', () => {
  test('empty -> empty string', () => {
    assert.equal(renderWikiContext([]), '')
  })
  test('includes titles and slugs', () => {
    const out = renderWikiContext([page('app-auth', 'JWT auth service', 'body')])
    assert.match(out, /prior work/i)
    assert.match(out, /JWT auth service \(app-auth\)/)
  })
})
