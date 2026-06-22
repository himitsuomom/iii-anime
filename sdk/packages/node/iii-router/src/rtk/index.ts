// RTK: compress tool_result content in LLM request bodies.
// Applied before the request is dispatched to a provider.
import { safeApply } from './applyFilter'
import { autoDetectFilter } from './autodetect'
import { MIN_COMPRESS_SIZE, RAW_CAP } from './constants'

export interface RtkHit {
  shape: string
  filter: string
  saved: number
}

export interface RtkStats {
  bytesBefore: number
  bytesAfter: number
  hits: RtkHit[]
}

// biome-ignore lint/suspicious/noExplicitAny: LLM request bodies are dynamically shaped
type AnyRecord = Record<string, any>

/**
 * Compress tool_result content in-place across the message shapes used by
 * Claude, OpenAI chat, OpenAI Responses, and Kiro. Returns stats or null when
 * disabled / not applicable.
 */
export function compressMessages(
  body: AnyRecord | null | undefined,
  enabled: boolean,
): RtkStats | null {
  if (!enabled) return null
  if (!body) return null

  if (body.conversationState) {
    return compressKiroFormat(body)
  }

  const items: AnyRecord[] | null = Array.isArray(body.messages)
    ? body.messages
    : Array.isArray(body.input)
      ? body.input
      : null
  if (!items) return null

  const stats: RtkStats = { bytesBefore: 0, bytesAfter: 0, hits: [] }
  try {
    for (const msg of items) {
      if (!msg) continue

      // OpenAI Responses — { type:"function_call_output", output: string | [{type:"input_text", text}] }
      if (msg.type === 'function_call_output') {
        if (typeof msg.output === 'string') {
          msg.output = compressText(msg.output, stats, 'openai-responses-string')
        } else if (Array.isArray(msg.output)) {
          for (const part of msg.output) {
            if (part && part.type === 'input_text' && typeof part.text === 'string') {
              part.text = compressText(part.text, stats, 'openai-responses-array')
            }
          }
        }
        continue
      }

      // OpenAI tool message — { role:"tool", content: "string" }
      if (msg.role === 'tool' && typeof msg.content === 'string') {
        msg.content = compressText(msg.content, stats, 'openai-tool')
        continue
      }

      if (!Array.isArray(msg.content)) continue

      // OpenAI tool message — { role:"tool", content:[{type:"text", text:"..."}] }
      if (msg.role === 'tool') {
        for (const part of msg.content) {
          if (part && part.type === 'text' && typeof part.text === 'string') {
            part.text = compressText(part.text, stats, 'openai-tool-array')
          }
        }
        continue
      }

      // Claude blocks array with tool_result entries
      for (const block of msg.content) {
        if (!block || block.type !== 'tool_result') continue
        if (block.is_error === true) continue // preserve error traces

        if (typeof block.content === 'string') {
          block.content = compressText(block.content, stats, 'claude-string')
        } else if (Array.isArray(block.content)) {
          for (const part of block.content) {
            if (part && part.type === 'text' && typeof part.text === 'string') {
              part.text = compressText(part.text, stats, 'claude-array')
            }
          }
        }
      }
    }
  } catch (e) {
    const message = e instanceof Error ? e.message : String(e)
    console.warn('[RTK] compressMessages error:', message)
    return null
  }
  return stats
}

// Kiro: conversationState.history[].userInputMessage.userInputMessageContext.toolResults[].content[].text
function compressKiroFormat(body: AnyRecord): RtkStats | null {
  const stats: RtkStats = { bytesBefore: 0, bytesAfter: 0, hits: [] }
  try {
    const state = body.conversationState
    const allMessages: AnyRecord[] = [...(Array.isArray(state?.history) ? state.history : [])]
    if (state?.currentMessage) allMessages.push(state.currentMessage)

    for (const msg of allMessages) {
      const toolResults = msg?.userInputMessage?.userInputMessageContext?.toolResults
      if (!Array.isArray(toolResults)) continue

      for (const tr of toolResults) {
        if (tr.status === 'error') continue // preserve error traces
        if (!Array.isArray(tr.content)) continue

        for (const part of tr.content) {
          if (part && typeof part.text === 'string') {
            part.text = compressText(part.text, stats, 'kiro-tool-result')
          }
        }
      }
    }
  } catch (e) {
    const message = e instanceof Error ? e.message : String(e)
    console.warn('[RTK] compressKiroFormat error:', message)
    return null
  }
  return stats
}

function compressText(text: string, stats: RtkStats, shape: string): string {
  const bytesIn = text.length
  stats.bytesBefore += bytesIn

  if (bytesIn < MIN_COMPRESS_SIZE || bytesIn > RAW_CAP) {
    stats.bytesAfter += bytesIn
    return text
  }

  const fn = autoDetectFilter(text)
  if (!fn) {
    stats.bytesAfter += bytesIn
    return text
  }

  const out = safeApply(fn, text)

  // Safety: never return empty, never grow the input
  if (!out || out.length === 0 || out.length >= bytesIn) {
    stats.bytesAfter += bytesIn
    return text
  }

  stats.bytesAfter += out.length
  stats.hits.push({ shape, filter: fn.filterName || fn.name, saved: bytesIn - out.length })
  return out
}

/** Format a one-line log summary from stats, or null if nothing was compressed. */
export function formatRtkLog(stats: RtkStats | null): string | null {
  if (!stats || !stats.hits || stats.hits.length === 0) return null
  const saved = stats.bytesBefore - stats.bytesAfter
  const pct = stats.bytesBefore > 0 ? ((saved / stats.bytesBefore) * 100).toFixed(1) : '0'
  const filters = Array.from(new Set(stats.hits.map(h => h.filter))).join(',')
  return `[RTK] saved ${saved}B / ${stats.bytesBefore}B (${pct}%) via [${filters}] hits=${stats.hits.length}`
}

export { autoDetectFilter } from './autodetect'
export { FILTERS } from './constants'
