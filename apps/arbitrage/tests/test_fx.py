"""FX込み利益計算のユニットテスト（オフライン）。"""

from __future__ import annotations

from src.domain.models import Money
from src.fx.calculator import build_fx_rate, calculate_profit, compute_effective_rate


def test_effective_rate_is_pessimistic() -> None:
    # バッファ 5% は base→quote 換算で得られる quote が少なくなる向き。
    assert compute_effective_rate(150.0, 5.0) == 150.0 * 0.95


def test_build_fx_rate_carries_buffer() -> None:
    fx = build_fx_rate(base="USD", quote="JPY", rate=150.0, buffer_percent=5.0, as_of="t")
    assert fx.effective_rate == 142.5
    assert fx.buffer_percent == 5.0
    assert fx.source == "static-config"


def test_profit_meets_floor_for_good_margin() -> None:
    fx = build_fx_rate(base="USD", quote="JPY", rate=150.0, buffer_percent=5.0, as_of="t")
    # 売価 $200 (20000 cents), 仕入れ ¥8000, 送料 ¥2000。
    breakdown = calculate_profit(
        source_cost=Money(8000, "JPY"),
        sold_price=Money(20000, "USD"),
        fx=fx,
        floor_jpy=1500,
        min_margin_percent=20.0,
        ebay_fee_percent=13.0,
        payment_fee_percent=3.0,
        shipping_jpy=2000,
    )
    assert breakdown.net_profit.currency == "JPY"
    # gross ≈ 200 * 142.5 = 28500; 手数料 16% → net rev ≈ 23940; -8000 -2000 ≈ 13940
    assert breakdown.net_profit.amount > 1500
    assert breakdown.meets_floor is True


def test_profit_below_floor_is_rejected() -> None:
    fx = build_fx_rate(base="USD", quote="JPY", rate=150.0, buffer_percent=5.0, as_of="t")
    # 高い仕入れ・薄い売価で赤字寄り。
    breakdown = calculate_profit(
        source_cost=Money(25000, "JPY"),
        sold_price=Money(20000, "USD"),
        fx=fx,
        floor_jpy=1500,
        min_margin_percent=20.0,
        shipping_jpy=3000,
    )
    assert breakdown.meets_floor is False


def test_zero_revenue_does_not_crash() -> None:
    fx = build_fx_rate(base="USD", quote="JPY", rate=150.0, buffer_percent=5.0, as_of="t")
    breakdown = calculate_profit(
        source_cost=Money(1000, "JPY"),
        sold_price=Money(0, "USD"),
        fx=fx,
        floor_jpy=1500,
        min_margin_percent=20.0,
    )
    assert breakdown.margin_percent == 0.0
    assert breakdown.meets_floor is False
