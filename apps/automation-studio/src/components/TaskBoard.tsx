import { Plus, X } from 'lucide-react'
import { type FormEvent, useEffect, useState } from 'react'
import { loadJSON, saveJSON } from '../lib/storage.ts'
import { QUADRANTS, type Quadrant, type Task } from '../lib/types.ts'
import { PageHeader } from './ui.tsx'

const STORAGE_KEY = 'automation-studio.tasks'

const SEED: Task[] = [
  { id: 's1', title: '注文の梱包・発送', quadrant: 'doing' },
  { id: 's2', title: '新規仕入れ商品の選定', quadrant: 'deciding' },
  { id: 's3', title: '商品説明文のリライト', quadrant: 'delegating' },
  { id: 's4', title: '在庫自動発注ルールの設計', quadrant: 'designing' },
]

export function TaskBoard() {
  const [tasks, setTasks] = useState<Task[]>(() => loadJSON(STORAGE_KEY, SEED))
  const [title, setTitle] = useState('')
  const [quadrant, setQuadrant] = useState<Quadrant>('doing')

  useEffect(() => {
    saveJSON(STORAGE_KEY, tasks)
  }, [tasks])

  function addTask(e: FormEvent) {
    e.preventDefault()
    const text = title.trim()
    if (!text) return
    setTasks((prev) => [...prev, { id: crypto.randomUUID(), title: text, quadrant }])
    setTitle('')
  }

  function moveTask(id: string, next: Quadrant) {
    setTasks((prev) => prev.map((t) => (t.id === id ? { ...t, quadrant: next } : t)))
  }

  function removeTask(id: string) {
    setTasks((prev) => prev.filter((t) => t.id !== id))
  }

  return (
    <div className="mx-auto max-w-5xl px-8 py-8">
      <PageHeader
        title="4Dタスクボード"
        subtitle="Clockworkの4分類（実行・決定・委任・設計）でタスクを棚卸し。委任(Delegating)はAI/VAに任せる候補です。"
      />

      <form onSubmit={addTask} className="mb-6 flex flex-wrap gap-2">
        <input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="タスクを追加…"
          className="min-w-[12rem] flex-1 rounded-md border border-border bg-background px-3 py-2 text-sm outline-none placeholder:text-muted focus:border-accent"
        />
        <select
          value={quadrant}
          onChange={(e) => setQuadrant(e.target.value as Quadrant)}
          className="rounded-md border border-border bg-background px-3 py-2 text-sm outline-none focus:border-accent"
        >
          {QUADRANTS.map((q) => (
            <option key={q.id} value={q.id}>
              {q.label}
            </option>
          ))}
        </select>
        <button
          type="submit"
          className="flex items-center gap-1 rounded-md bg-accent px-3 py-2 text-sm font-semibold text-accent-foreground hover:bg-accent-hover"
        >
          <Plus className="h-4 w-4" /> 追加
        </button>
      </form>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        {QUADRANTS.map((q) => {
          const items = tasks.filter((t) => t.quadrant === q.id)
          return (
            <div key={q.id} className="rounded-lg border border-border-subtle bg-surface p-4">
              <div className="mb-3 flex items-center gap-2">
                <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: q.color }} />
                <span className="text-sm font-semibold">{q.label}</span>
                <span className="text-xs text-muted">· {q.hint}</span>
              </div>
              <div className="space-y-2">
                {items.length === 0 && <p className="py-3 text-center text-xs text-muted">タスクなし</p>}
                {items.map((t) => (
                  <div
                    key={t.id}
                    className="flex items-center gap-2 rounded-md border border-border-subtle bg-background px-3 py-2"
                  >
                    <span className="flex-1 text-sm">{t.title}</span>
                    <select
                      value={t.quadrant}
                      onChange={(e) => moveTask(t.id, e.target.value as Quadrant)}
                      aria-label="タスクを移動"
                      className="rounded border border-border bg-surface px-1.5 py-1 text-xs text-secondary outline-none"
                    >
                      {QUADRANTS.map((opt) => (
                        <option key={opt.id} value={opt.id}>
                          {opt.label}
                        </option>
                      ))}
                    </select>
                    <button
                      type="button"
                      onClick={() => removeTask(t.id)}
                      aria-label="削除"
                      className="text-muted hover:text-error"
                    >
                      <X className="h-4 w-4" />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
