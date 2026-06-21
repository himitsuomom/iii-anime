import assert from 'node:assert/strict'
import { describe, test } from 'node:test'
import { authEnabled, checkAuth } from './auth.js'
import { EnvSecretStore, assertNoSecretsInEnv } from './secrets.js'

describe('auth gate', () => {
  test('open when no token configured', () => {
    const env = {} as NodeJS.ProcessEnv
    assert.equal(authEnabled(env), false)
    assert.equal(checkAuth({}, env), true)
  })

  test('requires a matching bearer token when configured', () => {
    const env = { STUDIO_API_TOKEN: 'sekret' } as NodeJS.ProcessEnv
    assert.equal(authEnabled(env), true)
    assert.equal(checkAuth({}, env), false)
    assert.equal(checkAuth({ authorization: 'Bearer wrong' }, env), false)
    assert.equal(checkAuth({ authorization: 'Bearer sekret' }, env), true)
    assert.equal(checkAuth({ 'x-api-key': 'sekret' }, env), true)
    assert.equal(checkAuth({ Authorization: 'Bearer sekret' }, env), true)
  })

  test('handles array-valued headers', () => {
    const env = { STUDIO_API_TOKEN: 't' } as NodeJS.ProcessEnv
    assert.equal(checkAuth({ authorization: ['Bearer t'] }, env), true)
  })
})

describe('secrets', () => {
  test('EnvSecretStore reads STUDIO_SECRET_<NAME>', async () => {
    const store = new EnvSecretStore({ STUDIO_SECRET_GIT_TOKEN: 'ghp_x' } as NodeJS.ProcessEnv)
    assert.equal(await store.get('git-token'), 'ghp_x')
    assert.equal(await store.get('git_token'), 'ghp_x')
    assert.equal(await store.get('missing'), null)
  })

  test('assertNoSecretsInEnv blocks leaking secrets to the sandbox', () => {
    assert.doesNotThrow(() => assertNoSecretsInEnv({ PATH: '/bin', HOME: '/w', CI: '1' }))
    assert.throws(() => assertNoSecretsInEnv({ STUDIO_SECRET_GIT_TOKEN: 'x' }))
    assert.throws(() => assertNoSecretsInEnv({ STUDIO_API_TOKEN: 'x' }))
  })
})
