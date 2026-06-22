import { describe, expect, test } from 'bun:test'
import { checkFallbackError, getQuotaCooldown } from './routing/fallback'
import { detectFormat } from './routing/providers'
import { autoDetectFilter, compressMessages } from './rtk'

describe('rtk autodetect', () => {
  test('detects git diff', () => {
    const diff = 'diff --git a/foo.ts b/foo.ts\n@@ -1,3 +1,3 @@\n-old\n+new\n context'
    expect(autoDetectFilter(diff)?.filterName).toBe('git-diff')
  })

  test('detects grep output', () => {
    const out = 'src/a.ts:12:const x = 1\nsrc/a.ts:30:return x\nsrc/b.ts:4:import a'
    expect(autoDetectFilter(out)?.filterName).toBe('grep')
  })

  test('returns null for tiny unstructured text', () => {
    expect(autoDetectFilter('hello world')).toBeNull()
  })
})

describe('compressMessages', () => {
  test('compresses a large grep tool_result (claude string form)', () => {
    // Many matches across few files → grep caps to 10/file, so output shrinks.
    const big = Array.from(
      { length: 200 },
      (_, i) => `src/file${i % 3}.ts:${i}:match here line content padding for token saver test`,
    ).join('\n')
    const body = {
      messages: [
        { role: 'user', content: 'find usages' },
        { role: 'user', content: [{ type: 'tool_result', tool_use_id: 't1', content: big }] },
      ],
    }
    const stats = compressMessages(body, true)
    expect(stats).not.toBeNull()
    expect(stats?.bytesAfter).toBeLessThan(stats?.bytesBefore ?? 0)
    expect(stats?.hits.length).toBeGreaterThan(0)
  })

  test('preserves error tool_result traces', () => {
    const big = `${'x'.repeat(2000)}`
    const body = {
      messages: [
        { role: 'user', content: [{ type: 'tool_result', is_error: true, content: big }] },
      ],
    }
    const stats = compressMessages(body, true)
    expect(body.messages[0].content[0].content).toBe(big)
    expect(stats?.hits.length).toBe(0)
  })

  test('returns null when disabled', () => {
    expect(compressMessages({ messages: [] }, false)).toBeNull()
  })
})

describe('fallback classification', () => {
  test('rate limit text → exponential backoff', () => {
    const d = checkFallbackError(429, 'rate limit exceeded', 0)
    expect(d.shouldFallback).toBe(true)
    expect(d.newBackoffLevel).toBe(1)
    expect(d.cooldownMs).toBe(2000)
  })

  test('401 → long cooldown, no backoff', () => {
    const d = checkFallbackError(401, 'unauthorized')
    expect(d.shouldFallback).toBe(true)
    expect(d.cooldownMs).toBe(2 * 60 * 1000)
  })

  test('backoff grows exponentially', () => {
    expect(getQuotaCooldown(1)).toBe(2000)
    expect(getQuotaCooldown(2)).toBe(4000)
    expect(getQuotaCooldown(3)).toBe(8000)
  })
})

describe('detectFormat', () => {
  test('openai indicators win', () => {
    expect(detectFormat({ messages: [], response_format: { type: 'json_object' } })).toBe('openai')
  })

  test('anthropic system + messages', () => {
    expect(detectFormat({ system: 'you are helpful', messages: [] })).toBe('anthropic')
  })
})
