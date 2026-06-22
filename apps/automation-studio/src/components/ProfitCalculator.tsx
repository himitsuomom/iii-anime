import { useId, useMemo, useState } from 'react'
import { computeProfit } from '../lib/calc.ts'
import { PLATFORM_PRESETS } from '../lib/reportData.ts'
import { formatJpy } from '../lib/utils.ts'
import { Card, inputClass, Label, PageHeader } from './ui.tsx'

const yen = formatJpy
const pct = (n: number) => `${(n * 100).toFixed(1)}%`

export function ProfitCalculator() {
  const [cost, setCost] = useState(1000)
  const [sell, setSell] = useState(2500)
  const [qty, setQty] = useState(10)
  const [platformId, setPlatformId] = useState('mercari')
  const [feePercent, setFeePercent] = useState(10)
  const [paymentPercent, setPaymentPercent] = useState(3.6)
  const [shipping, setShipping] = useState(300)
  const [other, setOther] = useState(0)

  const ids = {
    cost: useId(),
    sell: useId(),
    qty: useId(),
    platform: useId(),
    fee: useId(),
    pay: useId(),
    ship: useId(),
    other: useId(),
  }

  const m = useMemo(
    () => computeProfit({ cost, sell, qty, feePercent, paymentPercent, shipping, other }),
    [cost, sell, qty, feePercent, paymentPercent, shipping, other],
  )

  function selectPlatform(id: string) {
    setPlatformId(id)
    const preset = PLATFORM_PRESETS.find((p) => p.id === id)
    if (preset && id !== 'custom') setFeePercent(preset.feePercent)
  }

  return (
    <div className="mx-auto max-w-5xl px-8 py-8">
      <PageHeader
        title="利益計算機"
        subtitle="転売・物販の利益を、手数料・送料・諸費用を差し引いて即時に試算します（API不要）。"
      />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card>
          <div className="grid grid-cols-2 gap-4">
            <NumberField id={ids.cost} label="仕入額（1個）" value={cost} onChange={setCost} suffix="円" />
            <NumberField id={ids.sell} label="販売価格（1個）" value={sell} onChange={setSell} suffix="円" />
            <NumberField id={ids.qty} label="販売数量" value={qty} onChange={setQty} suffix="個" />
            <div>
              <Label htmlFor={ids.platform}>販売先</Label>
              <select
                id={ids.platform}
                value={platformId}
                onChange={(e) => selectPlatform(e.target.value)}
                className={inputClass}
              >
                {PLATFORM_PRESETS.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.label}
                  </option>
                ))}
              </select>
            </div>
            <NumberField
              id={ids.fee}
              label="販売手数料"
              value={feePercent}
              onChange={setFeePercent}
              suffix="%"
              step={0.1}
            />
            <NumberField
              id={ids.pay}
              label="決済手数料"
              value={paymentPercent}
              onChange={setPaymentPercent}
              suffix="%"
              step={0.1}
            />
            <NumberField id={ids.ship} label="送料（1個）" value={shipping} onChange={setShipping} suffix="円" />
            <NumberField id={ids.other} label="その他費用（1個）" value={other} onChange={setOther} suffix="円" />
          </div>
        </Card>

        <Card className="flex flex-col justify-center">
          <div className="grid grid-cols-2 gap-4">
            <Metric label="1個あたり利益" value={yen(m.unitProfit)} positive={m.unitProfit > 0} big />
            <Metric label="利益率" value={pct(m.margin)} positive={m.margin > 0} big />
            <Metric label={`合計利益（${qty}個）`} value={yen(m.totalProfit)} positive={m.totalProfit > 0} />
            <Metric label="売上合計" value={yen(m.totalRevenue)} />
            <Metric label="手数料（1個）" value={yen(m.fees)} />
            <Metric label="損益分岐 販売価格" value={Number.isFinite(m.breakeven) ? yen(m.breakeven) : '—'} />
          </div>
          <p className="mt-5 text-xs leading-relaxed text-muted">
            ※ 手数料は販売価格に対する割合で計算します。損益分岐価格は、この価格以上で売れば赤字にならない目安です。
          </p>
        </Card>
      </div>
    </div>
  )
}

function NumberField({
  id,
  label,
  value,
  onChange,
  suffix,
  step,
}: {
  id: string
  label: string
  value: number
  onChange: (n: number) => void
  suffix?: string
  step?: number
}) {
  return (
    <div>
      <Label htmlFor={id}>{label}</Label>
      <div className="relative">
        <input
          id={id}
          type="number"
          inputMode="decimal"
          min={0}
          step={step ?? 1}
          value={Number.isNaN(value) ? '' : value}
          onChange={(e) => onChange(e.target.value === '' ? 0 : Math.max(0, Number(e.target.value)))}
          className={inputClass}
        />
        {suffix && (
          <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-xs text-muted">
            {suffix}
          </span>
        )}
      </div>
    </div>
  )
}

function Metric({ label, value, positive, big }: { label: string; value: string; positive?: boolean; big?: boolean }) {
  const color = positive === undefined ? 'text-foreground' : positive ? 'text-success' : 'text-error'
  return (
    <div className="rounded-md border border-border-subtle bg-background p-3">
      <div className="text-xs text-muted">{label}</div>
      <div className={`mt-1 font-semibold ${big ? 'text-2xl' : 'text-lg'} ${color}`}>{value}</div>
    </div>
  )
}
