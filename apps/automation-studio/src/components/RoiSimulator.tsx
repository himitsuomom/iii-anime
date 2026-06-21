import { useId, useMemo, useState } from 'react'
import { ROI_PHASES } from '../lib/reportData.ts'
import { Card, Label, PageHeader } from './ui.tsx'

const yen = (n: number) => `¥${Math.round(n).toLocaleString('ja-JP')}`

export function RoiSimulator() {
  const [phaseId, setPhaseId] = useState('growth')
  const [hours, setHours] = useState(80)
  const [wage, setWage] = useState(2000)
  const ids = { phase: useId(), hours: useId(), wage: useId() }

  const phase = ROI_PHASES.find((p) => p.id === phaseId) ?? ROI_PHASES[0]

  const calc = useMemo(() => {
    const [loFrac, hiFrac] = phase.hoursSaved
    const savedLo = hours * loFrac
    const savedHi = hours * hiFrac
    const valueLo = savedLo * wage
    const valueHi = savedHi * wage
    const [costLo, costHi] = phase.monthlyCostJpy
    const avgCost = (costLo + costHi) / 2 || 1
    const avgValue = (valueLo + valueHi) / 2
    return { savedLo, savedHi, valueLo, valueHi, roiX: avgValue / avgCost }
  }, [phase, hours, wage])

  return (
    <div className="mx-auto max-w-5xl px-8 py-8">
      <PageHeader
        title="ツール & ROIシミュレーター"
        subtitle="事業フェーズと現状の作業時間から、推奨ツール・コスト・削減効果を概算します（レポート §6.3 / §8.1）。"
      />

      <div className="mb-6 grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card>
          <div className="space-y-4">
            <div>
              <Label htmlFor={ids.phase}>事業フェーズ</Label>
              <select
                id={ids.phase}
                value={phaseId}
                onChange={(e) => setPhaseId(e.target.value)}
                className={inputClass}
              >
                {ROI_PHASES.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.label}
                  </option>
                ))}
              </select>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor={ids.hours}>現状の月間作業時間</Label>
                <input
                  id={ids.hours}
                  type="number"
                  value={hours}
                  onChange={(e) => setHours(Number(e.target.value) || 0)}
                  className={inputClass}
                />
              </div>
              <div>
                <Label htmlFor={ids.wage}>時給換算（円）</Label>
                <input
                  id={ids.wage}
                  type="number"
                  value={wage}
                  onChange={(e) => setWage(Number(e.target.value) || 0)}
                  className={inputClass}
                />
              </div>
            </div>
            <div className="rounded-md border border-border-subtle bg-background p-3 text-sm">
              <div className="text-muted">推奨ツール</div>
              <div className="mt-1">{phase.tools}</div>
              <div className="mt-3 flex justify-between text-sm">
                <span className="text-muted">月額コスト目安</span>
                <span>
                  {yen(phase.monthlyCostJpy[0])} 〜 {yen(phase.monthlyCostJpy[1])}
                </span>
              </div>
              <div className="mt-1 flex justify-between text-sm">
                <span className="text-muted">期待ROI</span>
                <span className="text-accent">{phase.expectedRoi}</span>
              </div>
            </div>
          </div>
        </Card>

        <Card className="flex flex-col justify-center">
          <div className="space-y-4">
            <Big label="月間削減時間（概算）" value={`${calc.savedLo.toFixed(0)} 〜 ${calc.savedHi.toFixed(0)} 時間`} />
            <Big label="人件費換算の削減効果" value={`${yen(calc.valueLo)} 〜 ${yen(calc.valueHi)}`} accent />
            <Big label="投資対効果（概算）" value={`約 ${calc.roiX.toFixed(1)} 倍`} accent />
          </div>
          <p className="mt-4 text-xs leading-relaxed text-muted">
            ※ レポートのフェーズ別削減率レンジに基づく概算です。実際の効果は業務内容により変動します。
          </p>
        </Card>
      </div>

      <Card>
        <h3 className="mb-3 text-sm font-semibold text-secondary">全フェーズ比較</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="text-xs text-muted">
              <tr className="border-b border-border-subtle">
                <th className="py-2 pr-4 font-medium">フェーズ</th>
                <th className="py-2 pr-4 font-medium">推奨ツール</th>
                <th className="py-2 pr-4 font-medium">月額コスト</th>
                <th className="py-2 font-medium">期待ROI</th>
              </tr>
            </thead>
            <tbody>
              {ROI_PHASES.map((p) => (
                <tr key={p.id} className={`border-b border-border-subtle/50 ${p.id === phaseId ? 'bg-hover' : ''}`}>
                  <td className="py-2 pr-4 font-medium">{p.label}</td>
                  <td className="py-2 pr-4 text-secondary">{p.tools}</td>
                  <td className="py-2 pr-4 whitespace-nowrap">
                    {yen(p.monthlyCostJpy[0])}〜{yen(p.monthlyCostJpy[1])}
                  </td>
                  <td className="py-2 text-accent">{p.expectedRoi}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  )
}

function Big({ label, value, accent }: { label: string; value: string; accent?: boolean }) {
  return (
    <div>
      <div className="text-xs text-muted">{label}</div>
      <div className={`mt-1 text-2xl font-semibold ${accent ? 'text-accent' : 'text-foreground'}`}>{value}</div>
    </div>
  )
}

const inputClass =
  'w-full rounded-md border border-border bg-background px-3 py-2 text-sm outline-none placeholder:text-muted focus:border-accent'
