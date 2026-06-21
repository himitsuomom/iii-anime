import assert from 'node:assert/strict'
import { afterEach, describe, test } from 'node:test'
import { assetArgs, assetsFromEnv } from './assets.js'
import { getFactory, listFactories, registerFactory, resetFactories } from './factory.js'

describe('assetArgs', () => {
  test('empty bundle -> no flags', () => {
    assert.deepEqual(assetArgs({}), [])
  })
  test('maps each asset to the right CLI flag', () => {
    const args = assetArgs({
      mcpConfig: ['/a/mcp.json', '/b/mcp.json'],
      addDirs: ['/skills'],
      pluginDirs: ['/plugins/p1'],
      pluginUrls: ['https://x/p.zip'],
      agentsJson: '{"r":{}}',
      settings: '/s.json',
      allowedTools: ['Bash', 'mcp__github'],
      model: 'claude-opus-4-8',
      fallbackModel: 'claude-sonnet-4-6',
    })
    assert.ok(args.includes('--mcp-config') && args.includes('/b/mcp.json'))
    assert.ok(args.includes('--add-dir') && args.includes('/skills'))
    assert.ok(args.includes('--plugin-dir') && args.includes('/plugins/p1'))
    assert.ok(args.includes('--plugin-url') && args.includes('https://x/p.zip'))
    assert.deepEqual(args.slice(args.indexOf('--agents'), args.indexOf('--agents') + 2), ['--agents', '{"r":{}}'])
    assert.ok(args.includes('--model') && args.includes('claude-opus-4-8'))
    assert.ok(args.includes('--fallback-model'))
    const ai = args.indexOf('--allowedTools')
    assert.deepEqual(args.slice(ai), ['--allowedTools', 'Bash', 'mcp__github'])
  })
})

describe('assetsFromEnv', () => {
  test('parses CSV env vars', () => {
    const a = assetsFromEnv({
      STUDIO_MCP_CONFIG: '/a.json, /b.json',
      STUDIO_ADD_DIRS: '/skills',
      STUDIO_MODEL: 'claude-opus-4-8',
    } as NodeJS.ProcessEnv)
    assert.deepEqual(a.mcpConfig, ['/a.json', '/b.json'])
    assert.deepEqual(a.addDirs, ['/skills'])
    assert.equal(a.model, 'claude-opus-4-8')
    assert.equal(a.pluginDirs, undefined)
  })
})

describe('factory registry (namespacing)', () => {
  afterEach(() => resetFactories())

  test('registers factories and exposes them', () => {
    registerFactory({ id: 'app-studio', title: 'App Studio', routePrefix: '', stateScope: 'studio', buildQueue: 'studio-build' })
    registerFactory({ id: 'video-studio', title: 'Video', routePrefix: '/video', stateScope: 'video', buildQueue: 'video-render' })
    assert.equal(listFactories().length, 2)
    assert.equal(getFactory('video-studio')?.stateScope, 'video')
  })

  test('rejects route-prefix and state-scope collisions', () => {
    registerFactory({ id: 'a', title: 'A', routePrefix: '', stateScope: 'studio', buildQueue: 'q1' })
    assert.throws(() =>
      registerFactory({ id: 'b', title: 'B', routePrefix: '', stateScope: 'other', buildQueue: 'q2' }),
    )
    assert.throws(() =>
      registerFactory({ id: 'c', title: 'C', routePrefix: '/c', stateScope: 'studio', buildQueue: 'q3' }),
    )
  })
})
