import { Copy, Loader2, Sparkles } from 'lucide-react'
import { type FormEvent, useId, useState } from 'react'
import { toast } from 'sonner'
import { generateDescription } from '../lib/api.ts'
import type { GeneratedDescription } from '../lib/types.ts'
import { Card, Label, PageHeader } from './ui.tsx'

export function DescriptionGenerator() {
  const [productName, setProductName] = useState('')
  const [features, setFeatures] = useState('')
  const [keywords, setKeywords] = useState('')
  const [tone, setTone] = useState('プロフェッショナルかつ親しみやすい')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<GeneratedDescription | null>(null)
  const ids = { name: useId(), features: useId(), keywords: useId(), tone: useId() }

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    if (!productName.trim()) {
      toast.error('商品名を入力してください。')
      return
    }
    setLoading(true)
    setResult(null)
    try {
      const data = await generateDescription({ productName, features, keywords, tone })
      setResult(data)
      toast.success('商品説明を生成しました。')
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '生成に失敗しました。')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="mx-auto max-w-5xl px-8 py-8">
      <PageHeader
        title="商品説明ジェネレーター"
        subtitle="商品情報からSEO最適化済みの説明文・タイトル・キーワードをClaudeが自動生成します。"
      />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card>
          <form onSubmit={onSubmit} className="space-y-4">
            <div>
              <Label htmlFor={ids.name}>商品名 *</Label>
              <input
                id={ids.name}
                value={productName}
                onChange={(e) => setProductName(e.target.value)}
                placeholder="例：レトロ風 真鍮製デスクランプ"
                className={inputClass}
              />
            </div>
            <div>
              <Label htmlFor={ids.features}>特徴・仕様</Label>
              <textarea
                id={ids.features}
                value={features}
                onChange={(e) => setFeatures(e.target.value)}
                rows={4}
                placeholder="素材、サイズ、用途、こだわりなど"
                className={inputClass}
              />
            </div>
            <div>
              <Label htmlFor={ids.keywords}>狙いたいキーワード</Label>
              <input
                id={ids.keywords}
                value={keywords}
                onChange={(e) => setKeywords(e.target.value)}
                placeholder="例：アンティーク, 間接照明, 書斎"
                className={inputClass}
              />
            </div>
            <div>
              <Label htmlFor={ids.tone}>トーン</Label>
              <input id={ids.tone} value={tone} onChange={(e) => setTone(e.target.value)} className={inputClass} />
            </div>
            <button
              type="submit"
              disabled={loading}
              className="flex w-full items-center justify-center gap-2 rounded-md bg-accent px-4 py-2.5 text-sm font-semibold text-accent-foreground transition-colors hover:bg-accent-hover disabled:opacity-60"
            >
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
              {loading ? '生成中…' : 'AIで生成'}
            </button>
          </form>
        </Card>

        <Card>
          {!result && !loading && (
            <div className="flex h-full min-h-[16rem] items-center justify-center text-center text-sm text-muted">
              左のフォームを入力して「AIで生成」を押すと、
              <br />
              ここに結果が表示されます。
            </div>
          )}
          {loading && (
            <div className="flex h-full min-h-[16rem] items-center justify-center text-sm text-muted">
              <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Claude が生成しています…
            </div>
          )}
          {result && <Result data={result} />}
        </Card>
      </div>
    </div>
  )
}

function Result({ data }: { data: GeneratedDescription }) {
  function copyAll() {
    const text = [
      data.title,
      '',
      data.description,
      '',
      ...data.bullets.map((b) => `・${b}`),
      '',
      `SEO: ${data.seoKeywords.join(', ')}`,
    ].join('\n')
    navigator.clipboard.writeText(text).then(
      () => toast.success('コピーしました。'),
      () => toast.error('コピーに失敗しました。'),
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between gap-2">
        <h3 className="text-base font-semibold">{data.title}</h3>
        <button
          type="button"
          onClick={copyAll}
          className="flex flex-shrink-0 items-center gap-1 rounded-md border border-border px-2 py-1 text-xs text-secondary hover:bg-hover"
        >
          <Copy className="h-3 w-3" /> コピー
        </button>
      </div>
      <p className="whitespace-pre-wrap text-sm leading-relaxed text-secondary">{data.description}</p>
      <ul className="space-y-1.5">
        {data.bullets.map((b) => (
          <li key={b} className="flex gap-2 text-sm">
            <span className="text-accent">▸</span>
            {b}
          </li>
        ))}
      </ul>
      <div className="flex flex-wrap gap-1.5 pt-1">
        {data.seoKeywords.map((k) => (
          <span key={k} className="rounded-full bg-hover px-2.5 py-0.5 text-xs text-secondary">
            {k}
          </span>
        ))}
      </div>
    </div>
  )
}

const inputClass =
  'w-full rounded-md border border-border bg-background px-3 py-2 text-sm outline-none placeholder:text-muted focus:border-accent'
