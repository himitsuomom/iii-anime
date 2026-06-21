import { LayoutDashboard, ListChecks, MessageSquare, Sparkles, Workflow } from 'lucide-react'
import { cn } from '../lib/utils.ts'

export type View = 'dashboard' | 'generator' | 'assistant' | 'tasks'

const NAV: { id: View; label: string; icon: typeof LayoutDashboard }[] = [
  { id: 'dashboard', label: 'ダッシュボード', icon: LayoutDashboard },
  { id: 'generator', label: '商品説明ジェネレーター', icon: Sparkles },
  { id: 'assistant', label: '問い合わせアシスタント', icon: MessageSquare },
  { id: 'tasks', label: '4Dタスクボード', icon: ListChecks },
]

interface SidebarProps {
  view: View
  onChange: (view: View) => void
}

export function Sidebar({ view, onChange }: SidebarProps) {
  return (
    <aside className="flex w-60 flex-shrink-0 flex-col border-r border-border-subtle bg-surface">
      <div className="flex items-center gap-2 px-5 py-5">
        <div className="flex h-8 w-8 items-center justify-center rounded-md bg-accent text-accent-foreground">
          <Workflow className="h-5 w-5" />
        </div>
        <div>
          <div className="text-sm font-semibold leading-tight">Automation Studio</div>
          <div className="text-xs text-muted">AI業務自動化</div>
        </div>
      </div>

      <nav className="flex flex-1 flex-col gap-1 px-3">
        {NAV.map((item) => {
          const Icon = item.icon
          const active = view === item.id
          return (
            <button
              key={item.id}
              type="button"
              onClick={() => onChange(item.id)}
              className={cn(
                'flex items-center gap-3 rounded-md px-3 py-2 text-left text-sm transition-colors',
                active ? 'bg-hover font-medium text-foreground' : 'text-secondary hover:bg-hover hover:text-foreground',
              )}
            >
              <Icon className={cn('h-4 w-4', active && 'text-accent')} />
              {item.label}
            </button>
          )
        })}
      </nav>

      <div className="px-5 py-4 text-xs leading-relaxed text-muted">
        「80%をAIに任せ、20%を人が仕上げる」
        <br />
        週4時間ワークの実践ツール
      </div>
    </aside>
  )
}
