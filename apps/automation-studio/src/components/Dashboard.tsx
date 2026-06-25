import { Calculator, Map as MapIcon, MessageSquare, Package, Sparkles, TrendingUp } from 'lucide-react'
import { useEffect, useState } from 'react'
import { fetchStats, type RuntimeStats } from '../lib/api.ts'
import type { View } from './Sidebar.tsx'
import { Card, PageHeader } from './ui.tsx'

interface Kpi {
  label: string
  value: string
  delta: string
  positive: boolean
  icon: typeof TrendingUp
}

// 売上・在庫は実データソース（受注DB）が無いためサンプル。AI稼働数はサーバ実測値（下記）。
const SAMPLE_KPIS: Kpi[] = [
  { label: '月間売上（サンプル）', value: '¥1,284,000', delta: 'サンプル値', positive: true, icon: TrendingUp },
  { label: '在庫アラート（サンプル）', value: '3件', delta: 'サンプル値', positive: false, icon: Package },
]

export function Dashboard({ onNavigate }: { onNavigate: (view: View) => void }) {
  const [stats, setStats] = useState<RuntimeStats | null>(null)

  useEffect(() => {
    let alive = true
    fetchStats()
      .then((s) => {
        if (alive) setStats(s)
      })
      .catch(() => {
        /* オフライン/未起動時は実測カードを「—」表示にフォールバック */
      })
    return () => {
      alive = false
    }
  }, [])

  const live = stats ? `${stats.model}${stats.workerConnected ? ' · worker接続' : ''}` : '取得中…'

  return (
    <div className="mx-auto max-w-5xl px-8 py-8">
      <PageHeader title="ダッシュボード" subtitle="「自分がいなくても回る仕組み」の稼働状況を一画面で把握します。" />

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {/* サーバ実測値（/api/stats） */}
        <Card>
          <div className="flex items-center justify-between">
            <span className="text-xs text-muted">AI説明生成数</span>
            <Sparkles className="h-4 w-4 text-muted" />
          </div>
          <div className="mt-3 text-2xl font-semibold">{stats ? stats.descriptionsGenerated : '—'}</div>
          <div className="mt-1 text-xs text-success">{live}</div>
        </Card>
        <Card>
          <div className="flex items-center justify-between">
            <span className="text-xs text-muted">問い合わせ自動応答数</span>
            <MessageSquare className="h-4 w-4 text-muted" />
          </div>
          <div className="mt-3 text-2xl font-semibold">{stats ? stats.inquiriesAnswered : '—'}</div>
          <div className="mt-1 text-xs text-success">{stats?.hasApiKey ? 'Claude応答' : 'オフライン応答'}</div>
        </Card>
        {SAMPLE_KPIS.map((kpi) => {
          const Icon = kpi.icon
          return (
            <Card key={kpi.label}>
              <div className="flex items-center justify-between">
                <span className="text-xs text-muted">{kpi.label}</span>
                <Icon className="h-4 w-4 text-muted" />
              </div>
              <div className="mt-3 text-2xl font-semibold">{kpi.value}</div>
              <div className={kpi.positive ? 'mt-1 text-xs text-success' : 'mt-1 text-xs text-warning'}>
                {kpi.delta}
              </div>
            </Card>
          )
        })}
      </div>

      <h2 className="mt-10 mb-3 text-sm font-semibold text-secondary">クイックアクション</h2>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <ActionCard
          icon={Sparkles}
          title="商品説明をAIで生成"
          body="商品情報を入力するだけで、SEO最適化された説明文・タイトル・キーワードを自動生成。"
          onClick={() => onNavigate('generator')}
        />
        <ActionCard
          icon={MessageSquare}
          title="問い合わせAIアシスタント"
          body="お客様からの質問に24時間自動応答。一次対応を80%自動化します。"
          onClick={() => onNavigate('assistant')}
        />
        <ActionCard
          icon={Calculator}
          title="利益計算機"
          body="仕入・販売価格・手数料から、転売・物販の利益と損益分岐を即試算（API不要）。"
          onClick={() => onNavigate('profit')}
        />
        <ActionCard
          icon={MapIcon}
          title="実践ロードマップ"
          body="「週4時間」体制へ向けた5ステップを、進捗チェックしながら実行。"
          onClick={() => onNavigate('roadmap')}
        />
      </div>
    </div>
  )
}

function ActionCard({
  icon: Icon,
  title,
  body,
  onClick,
}: {
  icon: typeof Sparkles
  title: string
  body: string
  onClick: () => void
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="rounded-lg border border-border-subtle bg-surface p-5 text-left transition-colors hover:border-border hover:bg-elevated"
    >
      <div className="flex items-center gap-2">
        <Icon className="h-4 w-4 text-accent" />
        <span className="font-medium">{title}</span>
      </div>
      <p className="mt-2 text-sm text-secondary">{body}</p>
    </button>
  )
}
