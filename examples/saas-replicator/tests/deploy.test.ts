import assert from 'node:assert/strict'
import { test } from 'node:test'
import { MemoryEngine } from '../src/adapters/memoryEngine'
import { deploy } from '../src/deploy'
import type { Codebase } from '../src/logic/artifacts'
import { buildDeployPlan } from '../src/logic/deploy'

const codebase: Codebase = {
  target: 'Trello',
  files: [
    { path: 'src/app.mjs', content: 'export const createApp = () => ({})' },
    { path: 'test.mjs', content: 'console.log("TESTS total=1 passed=1 failed=0")' },
  ],
  testFile: 'test.mjs',
}

test('buildDeployPlan picks the app entrypoint and lists steps', () => {
  const plan = buildDeployPlan(codebase)
  assert.equal(plan.entrypoint, 'src/app.mjs')
  assert.equal(plan.files.length, 2)
  assert.ok(plan.steps.length > 0)
  assert.ok(plan.steps.some((s) => s.includes('publish')))
})

test('deploy simulates when no deploy worker is present', async () => {
  const dep = await deploy(new MemoryEngine(), codebase)
  assert.equal(dep.status, 'simulated')
  assert.ok(dep.url.endsWith('.local'))
  assert.equal(dep.entrypoint, 'src/app.mjs')
})

test('deploy publishes via a deploy worker when present', async () => {
  const engine = new MemoryEngine([{ name: 'vercel' }])
  engine.register('vercel::publish', async () => ({ url: 'https://trello.vercel.app' }))
  const dep = await deploy(engine, codebase)
  assert.equal(dep.status, 'deployed')
  assert.equal(dep.url, 'https://trello.vercel.app')
})

test('deploy falls back to simulated if the worker throws', async () => {
  const engine = new MemoryEngine([{ name: 'deploy' }])
  engine.register('deploy::publish', async () => {
    throw new Error('boom')
  })
  const dep = await deploy(engine, codebase)
  assert.equal(dep.status, 'simulated')
})
