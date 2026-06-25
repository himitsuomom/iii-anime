import type { ChatMessage, GeneratedDescription } from './types.ts'

export interface GenerateInput {
  productName: string
  features: string
  keywords: string
  tone: string
}

async function readError(res: Response): Promise<string> {
  try {
    const data = await res.json()
    if (data && typeof data.error === 'string') return data.error
  } catch {
    // fall through
  }
  return `リクエストに失敗しました (HTTP ${res.status})`
}

export async function fetchHealth(): Promise<{ ok: boolean; hasApiKey: boolean }> {
  const res = await fetch('/api/health')
  if (!res.ok) throw new Error(await readError(res))
  return res.json()
}

export interface RuntimeStats {
  descriptionsGenerated: number
  inquiriesAnswered: number
  hasApiKey: boolean
  model: string
  workerConnected: boolean
}

export async function fetchStats(): Promise<RuntimeStats> {
  const res = await fetch('/api/stats')
  if (!res.ok) throw new Error(await readError(res))
  return res.json()
}

export interface GenerateResult {
  result: GeneratedDescription
  source: 'claude' | 'template'
}

export async function generateDescription(input: GenerateInput): Promise<GenerateResult> {
  const res = await fetch('/api/generate-description', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(input),
  })
  if (!res.ok) throw new Error(await readError(res))
  const data = await res.json()
  return { result: data.result as GeneratedDescription, source: data.source === 'claude' ? 'claude' : 'template' }
}

/**
 * Streams an assistant reply token-by-token. Calls `onDelta` for each chunk and
 * resolves with the full text. Throws if the server emits an error event.
 */
export async function streamChat(messages: ChatMessage[], onDelta: (text: string) => void): Promise<string> {
  const res = await fetch('/api/chat', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ messages }),
  })
  if (!res.ok || !res.body) throw new Error(await readError(res))

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let full = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })

    const chunks = buffer.split('\n\n')
    buffer = chunks.pop() ?? ''

    for (const chunk of chunks) {
      let eventName = 'message'
      let data = ''
      for (const line of chunk.split('\n')) {
        if (line.startsWith('event:')) eventName = line.slice(6).trim()
        else if (line.startsWith('data:')) data += line.slice(5).trim()
      }
      if (!data) continue

      if (eventName === 'delta') {
        const text = JSON.parse(data).text as string
        full += text
        onDelta(text)
      } else if (eventName === 'error') {
        throw new Error(JSON.parse(data).error ?? '応答の生成に失敗しました。')
      }
    }
  }

  return full
}
