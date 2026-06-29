import { Check } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { PRINCIPLES, ROADMAP_STEPS } from '../lib/reportData.ts'
import { loadJSON, saveJSON } from '../lib/storage.ts'
import { cn } from '../lib/utils.ts'
import { Card, PageHeader } from './ui.tsx'

const STORAGE_KEY = 'automation-studio.roadmap'

function actionKey(stepId: string, index: number) {
  return `${stepId}:${index}`
}

export function Roadmap() {
  const [done, setDone] = useState<Record<string, boolean>>(() => loadJSON(STORAGE_KEY, {}))

  useEffect(() => {
    saveJSON(STORAGE_KEY, done)
  }, [done])

  const { total, completed } = useMemo(() => {
    const all = ROADMAP_STEPS.flatMap((s) => s.actions.map((_, i) => actionKey(s.id, i)))
    return { total: all.length, completed: all.filter((k) => done[k]).length }
  }, [done])

  function toggle(key: string) {
    setDone((prev) => ({ ...prev, [key]: !prev[key] }))
  }

  const progress = total > 0 ? Math.round((completed / total) * 100) : 0

  return (
    <div className="mx-auto max-w-5xl px-8 py-8">
      <PageHeader
        title="実践ロードマップ"
        subtitle="「週4時間」体制へ向けた5ステップ。チェックは自動保存されます（レポート §11.2）。"
      />

      <Card className="mb-6">
        <div className="flex items-center justify-between text-sm">
          <span className="font-medium">進捗</span>
          <span className="text-muted">
            {completed} / {total} 完了（{progress}%）
          </span>
        </div>
        <div className="mt-2 h-2 overflow-hidden rounded-full bg-hover">
          <div className="h-full rounded-full bg-accent transition-all" style={{ width: `${progress}%` }} />
        </div>
      </Card>

      <div className="space-y-4">
        {ROADMAP_STEPS.map((step) => (
          <Card key={step.id}>
            <div className="flex items-baseline gap-3">
              <span className="rounded bg-hover px-2 py-0.5 text-xs font-medium text-accent">{step.period}</span>
              <h3 className="text-base font-semibold">{step.title}</h3>
              <span className="ml-auto text-xs text-muted">
                {step.cost}・{step.outcome}
              </span>
            </div>
            <ul className="mt-3 space-y-2">
              {step.actions.map((action, i) => {
                const key = actionKey(step.id, i)
                const checked = Boolean(done[key])
                return (
                  <li key={key}>
                    <button
                      type="button"
                      onClick={() => toggle(key)}
                      className="flex w-full items-center gap-3 text-left text-sm"
                    >
                      <span
                        className={cn(
                          'flex h-5 w-5 flex-shrink-0 items-center justify-center rounded border',
                          checked ? 'border-accent bg-accent text-accent-foreground' : 'border-border',
                        )}
                      >
                        {checked && <Check className="h-3.5 w-3.5" />}
                      </span>
                      <span className={checked ? 'text-muted line-through' : ''}>{action}</span>
                    </button>
                  </li>
                )
              })}
            </ul>
          </Card>
        ))}
      </div>

      <h2 className="mt-10 mb-3 text-sm font-semibold text-secondary">成功の5原則</h2>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        {PRINCIPLES.map((p) => (
          <Card key={p.title}>
            <div className="text-sm font-medium">{p.title}</div>
            <p className="mt-1 text-sm text-secondary">{p.body}</p>
          </Card>
        ))}
      </div>
    </div>
  )
}
