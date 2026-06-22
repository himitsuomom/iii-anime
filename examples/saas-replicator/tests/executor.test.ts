import assert from 'node:assert/strict'
import { test } from 'node:test'
import { MemoryEngine } from '../src/adapters/memoryEngine'
import { localExecutor, pickExecutor } from '../src/executor'
import { parseTestStdout } from '../src/logic/artifacts'

test('localExecutor runs inline node code and captures a TESTS summary', async () => {
  const exec = localExecutor()
  assert.equal(exec.kind, 'local')
  const result = await exec.run({
    lang: 'node',
    code: "const c=[1+1===2,2*2===4]; console.log('TESTS total=' + c.length + ' passed=' + c.filter(Boolean).length + ' failed=0')",
  })
  assert.equal(result.success, true)
  assert.equal(result.exit_code, 0)
  const report = parseTestStdout(result.stdout, false)
  assert.equal(report.total, 2)
  assert.equal(report.passed, 2)
})

test('localExecutor reports failure on a non-zero exit', async () => {
  const result = await localExecutor().run({ lang: 'node', code: 'process.exit(3)' })
  assert.equal(result.success, false)
  assert.equal(result.exit_code, 3)
})

test('pickExecutor selects sandbox when iii-sandbox is present, else local', async () => {
  const withSandbox = await pickExecutor(new MemoryEngine([{ name: 'iii-sandbox' }]))
  assert.equal(withSandbox.kind, 'sandbox')

  const withoutSandbox = await pickExecutor(new MemoryEngine())
  assert.equal(withoutSandbox.kind, 'local')
})
