import { Loader2, Send } from 'lucide-react'
import { type FormEvent, useEffect, useRef, useState } from 'react'
import { toast } from 'sonner'
import { streamChat } from '../lib/api.ts'
import type { ChatMessage } from '../lib/types.ts'
import { cn } from '../lib/utils.ts'
import { PageHeader } from './ui.tsx'

const SUGGESTIONS = ['配送にかかる日数は？', '返品はできますか？', 'この商品の在庫はありますか？']

export function Assistant() {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)

  // biome-ignore lint/correctness/useExhaustiveDependencies: scroll on every message change
  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight })
  }, [messages])

  async function send(text: string) {
    const content = text.trim()
    if (!content || busy) return
    const history: ChatMessage[] = [...messages, { role: 'user', content }]
    setMessages([...history, { role: 'assistant', content: '' }])
    setInput('')
    setBusy(true)
    try {
      await streamChat(history, (delta) => {
        setMessages((prev) => {
          const copy = [...prev]
          const last = copy[copy.length - 1]
          copy[copy.length - 1] = { ...last, content: last.content + delta }
          return copy
        })
      })
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '応答に失敗しました。')
      setMessages((prev) => prev.filter((m, i) => !(i === prev.length - 1 && m.role === 'assistant' && !m.content)))
    } finally {
      setBusy(false)
    }
  }

  function onSubmit(e: FormEvent) {
    e.preventDefault()
    void send(input)
  }

  return (
    <div className="mx-auto flex h-full max-w-3xl flex-col px-8 py-8">
      <PageHeader title="問い合わせアシスタント" subtitle="お客様の質問にClaudeがリアルタイムで自動応答します。" />

      <div ref={scrollRef} className="flex-1 space-y-4 overflow-y-auto pb-4">
        {messages.length === 0 && (
          <div className="space-y-4 pt-8 text-center">
            <p className="text-sm text-muted">よくある質問の例：</p>
            <div className="flex flex-wrap justify-center gap-2">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  type="button"
                  onClick={() => void send(s)}
                  className="rounded-full border border-border px-3 py-1.5 text-sm text-secondary hover:bg-hover"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((m, i) => (
          <div key={`${m.role}-${i}`} className={cn('flex', m.role === 'user' ? 'justify-end' : 'justify-start')}>
            <div
              className={cn(
                'max-w-[80%] whitespace-pre-wrap rounded-lg px-4 py-2.5 text-sm leading-relaxed',
                m.role === 'user'
                  ? 'bg-accent text-accent-foreground'
                  : 'border border-border-subtle bg-surface text-foreground',
              )}
            >
              {m.content || (busy && <Loader2 className="h-4 w-4 animate-spin text-muted" />)}
            </div>
          </div>
        ))}
      </div>

      <form onSubmit={onSubmit} className="flex gap-2 border-t border-border-subtle pt-4">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="メッセージを入力…"
          disabled={busy}
          className="flex-1 rounded-md border border-border bg-background px-3 py-2.5 text-sm outline-none placeholder:text-muted focus:border-accent disabled:opacity-60"
        />
        <button
          type="submit"
          disabled={busy || !input.trim()}
          className="flex items-center justify-center rounded-md bg-accent px-4 text-accent-foreground transition-colors hover:bg-accent-hover disabled:opacity-60"
        >
          <Send className="h-4 w-4" />
        </button>
      </form>
    </div>
  )
}
