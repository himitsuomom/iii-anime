import { registerWorker, type ApiRequest, type ApiResponse } from 'iii-sdk'

const iii = registerWorker(process.env.III_URL ?? 'ws://localhost:49134')

iii.registerFunction(
  'hello::greet',
  async (req: ApiRequest<{ name?: string }>): Promise<ApiResponse> => {
    const name = req?.body?.name ?? 'world'
    console.log('Greeting user', { name })
    return {
      status_code: 200,
      headers: { 'Content-Type': 'application/json' },
      body: { message: `Hello, ${name}!` },
    }
  },
  { description: 'Greet a user by name' },
)

iii.registerTrigger({
  type: 'http',
  function_id: 'hello::greet',
  config: { api_path: '/hello', http_method: 'POST' },
})

// --- core-primitives demo: a state-backed counter ---
// Persists across calls via the iii-state worker, invoked function-to-function
// with iii.trigger (state::get / state::set).
iii.registerFunction(
  'counter::bump',
  async (req: ApiRequest<{ by?: number }>): Promise<ApiResponse> => {
    const by = req?.body?.by ?? 1
    const scope = 'demo'
    const key = 'counter'
    const current = (await iii.trigger({
      function_id: 'state::get',
      payload: { scope, key },
    })) as number | null
    const next = (current ?? 0) + by
    await iii.trigger({
      function_id: 'state::set',
      payload: { scope, key, value: next },
    })
    console.log('counter bumped', { by, next })
    return {
      status_code: 200,
      headers: { 'Content-Type': 'application/json' },
      body: { counter: next, incremented_by: by },
    }
  },
  { description: 'Increment a persistent counter held in iii-state' },
)

iii.registerTrigger({
  type: 'http',
  function_id: 'counter::bump',
  config: { api_path: '/counter', http_method: 'POST' },
})

console.log(
  'hello-demo worker registered: POST /hello -> hello::greet, POST /counter -> counter::bump',
)
