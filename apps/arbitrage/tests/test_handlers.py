"""純粋ハンドラのユニットテスト（オフライン・dry-run）。"""

from __future__ import annotations

import pytest

from src.worker.handlers import (
    handle_evaluate,
    handle_fx_rate,
    handle_notify_telegram,
    handle_profit_calc,
    handle_research_comps,
    handle_source_scan,
)
from src.worker.services import Services, build_services


@pytest.fixture
def services() -> Services:
    # 明示的に dry-run・オフライン。
    return build_services(force_offline=True, dry_run=True)


def test_source_scan_returns_candidates(services: Services) -> None:
    out = handle_source_scan({"marketplace": "snkrdunk", "query": "sneaker", "limit": 3}, services)
    assert out["count"] == 3
    assert out["candidates"][0]["marketplace"] == "snkrdunk"
    assert out["candidates"][0]["price"]["currency"] == "JPY"


def test_research_comps_returns_median(services: Services) -> None:
    out = handle_research_comps({"title": "sneaker", "limit": 5}, services)
    assert out["count"] == 5
    assert out["median"]["currency"] == "USD"
    assert out["median"]["amount"] > 0


def test_fx_rate_applies_buffer(services: Services) -> None:
    out = handle_fx_rate({"rate": 150.0}, services)
    assert out["effectiveRate"] == 142.5
    assert out["base"] == "USD"
    assert out["quote"] == "JPY"


def test_profit_calc_and_evaluate_list(services: Services) -> None:
    profit = handle_profit_calc(
        {
            "sourceCost": {"amount": 8000, "currency": "JPY"},
            "soldPrice": {"amount": 20000, "currency": "USD"},
            "shippingJpy": 2000,
        },
        services,
    )
    assert profit["meetsFloor"] is True
    decision = handle_evaluate({"profit": profit}, services)
    assert decision["decision"] == "list"


def test_evaluate_skips_below_floor(services: Services) -> None:
    profit = handle_profit_calc(
        {
            "sourceCost": {"amount": 25000, "currency": "JPY"},
            "soldPrice": {"amount": 20000, "currency": "USD"},
            "shippingJpy": 3000,
        },
        services,
    )
    decision = handle_evaluate({"profit": profit}, services)
    assert decision["decision"] == "skip"
    assert decision["reasons"]


def test_notify_dry_run_does_not_send(services: Services) -> None:
    out = handle_notify_telegram({"text": "売れました", "sourceUrl": "https://x.invalid/i/1"}, services)
    assert out["dryRun"] is True
    assert "売れました" in out["preview"]
    assert "https://x.invalid/i/1" in out["preview"]
