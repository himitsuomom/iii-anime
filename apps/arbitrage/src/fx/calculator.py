"""FX込み利益計算（M3/M4）。純関数・エンジン非依存。

通貨の最小単位の約束（Phase 0）:
  - JPY: amount = 円（小数なし）
  - USD: amount = セント（1ドル = 100）

為替バッファは**悲観側**に倒す。USD売上を円に換算する際、得られる円が少なくなる向き
（`effective_rate = rate * (1 - buffer/100)`）で計算するため、¥利益フロアは過大評価されない
（マスター指示書 §3-6）。
"""

from __future__ import annotations

from src.domain.models import FxRate, Money, ProfitBreakdown


def compute_effective_rate(rate: float, buffer_percent: float) -> float:
    """バッファ適用後の実効レート（base→quote 換算で悲観側）。"""
    return rate * (1.0 - buffer_percent / 100.0)


def build_fx_rate(
    *,
    base: str,
    quote: str,
    rate: float,
    buffer_percent: float,
    as_of: str,
    source: str = "static-config",
) -> FxRate:
    """生レートとバッファから FxRate を組み立てる。"""
    return FxRate(
        base=base,
        quote=quote,
        rate=rate,
        buffer_percent=buffer_percent,
        effective_rate=compute_effective_rate(rate, buffer_percent),
        as_of=as_of,
        source=source,
    )


def _to_quote(amount_minor_base: int, effective_rate: float) -> int:
    """base の最小単位額（USD セント）を quote（JPY 円）へ換算する。

    USD は 100 セント = 1 ドル前提。四捨五入して整数円を返す。
    """
    return round(amount_minor_base / 100.0 * effective_rate)


def calculate_profit(
    *,
    source_cost: Money,
    sold_price: Money,
    fx: FxRate,
    floor_jpy: int,
    min_margin_percent: float,
    ebay_fee_percent: float = 13.0,
    payment_fee_percent: float = 3.0,
    shipping_jpy: int = 0,
) -> ProfitBreakdown:
    """全経費控除後の純利益（円）を算出する。

    Args:
        source_cost: 国内仕入れ価格（JPY, 円）。
        sold_price: eBay 想定売価（base 通貨, USD セント）。
        fx: 実効レートを持つ FxRate。
        floor_jpy / min_margin_percent: 判定閾値。
        ebay_fee_percent / payment_fee_percent: 売価に対する手数料率（%）。
        shipping_jpy: 国際送料（円）。
    """
    revenue_base = sold_price.amount  # USD セント
    ebay_fee_base = round(revenue_base * ebay_fee_percent / 100.0)
    payment_fee_base = round(revenue_base * payment_fee_percent / 100.0)
    net_revenue_base = revenue_base - ebay_fee_base - payment_fee_base

    # 悲観レートで円換算。
    net_revenue_jpy = _to_quote(net_revenue_base, fx.effective_rate)
    gross_revenue_jpy = _to_quote(revenue_base, fx.effective_rate)

    net_profit_jpy = net_revenue_jpy - source_cost.amount - shipping_jpy

    margin_percent = (net_profit_jpy / gross_revenue_jpy * 100.0) if gross_revenue_jpy > 0 else 0.0
    meets_floor = net_profit_jpy >= floor_jpy and margin_percent >= min_margin_percent

    return ProfitBreakdown(
        source_cost=source_cost,
        sold_price=sold_price,
        fx_rate=fx,
        net_profit=Money(amount=net_profit_jpy, currency=fx.quote),
        margin_percent=round(margin_percent, 2),
        meets_floor=meets_floor,
        ebay_fee=Money(amount=ebay_fee_base, currency=sold_price.currency),
        payment_fee=Money(amount=payment_fee_base, currency=sold_price.currency),
        shipping_cost=Money(amount=shipping_jpy, currency=fx.quote),
    )
