"""Phase 2: 分類・出品リストのテスト（オフライン・mocked state）。"""

from __future__ import annotations

from typing import Any

import pytest

from src.classify.classifier import price_band
from src.config import load_settings
from src.worker.handlers import handle_classify, handle_listing_list
from src.worker.services import Services, build_services
from src.worker.store import LISTING_LIST_SCOPE


class _FakeStateEngine:
    def __init__(self) -> None:
        self.store: dict[tuple[str, str], Any] = {}

    def trigger(self, req: dict[str, Any]) -> Any:
        fid = req["function_id"]
        p = req.get("payload", {})
        if fid == "state::set":
            self.store[(p["scope"], p["key"])] = p["value"]
            return {"new_value": p["value"]}
        if fid == "state::list":
            return [v for (s, _), v in self.store.items() if s == p["scope"]]
        if fid == "state::get":
            return self.store.get((p["scope"], p["key"]))
        raise AssertionError(fid)


@pytest.fixture
def services() -> Services:
    return build_services(force_offline=True, dry_run=True)


def test_price_band_thresholds() -> None:
    cfg = load_settings().classify
    assert price_band(3000, cfg) == "small"
    assert price_band(cfg.small_max_jpy, cfg) == "small"
    assert price_band(cfg.small_max_jpy + 1, cfg) == "medium"
    assert price_band(cfg.medium_max_jpy + 1, cfg) == "large"


def _item(idx: int, price_jpy: int, decision: str = "list") -> dict[str, Any]:
    return {
        "sourceListing": {
            "id": f"mercari-{idx}",
            "marketplace": "mercari",
            "url": f"https://x.invalid/{idx}",
            "title": "item",
            "price": {"amount": price_jpy, "currency": "JPY"},
            "fetchedAt": "2026-06-29T00:00:00Z",
        },
        "profit": {"netProfit": {"amount": 3000, "currency": "JPY"}, "meetsFloor": decision == "list"},
        "decision": decision,
        "category": "sneakers",
    }


def test_classify_persists_and_buckets(services: Services) -> None:
    engine = _FakeStateEngine()
    out = handle_classify(
        {"items": [_item(1, 3000), _item(2, 12000), _item(3, 30000)]},
        services,
        engine.trigger,
    )
    assert out["count"] == 3
    assert out["byBand"] == {"small": 1, "medium": 1, "large": 1}
    assert out["byMarketplace"] == {"mercari": 3}
    # 出品リストに永続化される。
    assert engine.store[(LISTING_LIST_SCOPE, "mercari-1")]["priceBand"] == "small"


def test_classify_filters_non_listable(services: Services) -> None:
    engine = _FakeStateEngine()
    out = handle_classify(
        {"items": [_item(1, 3000, "list"), _item(2, 4000, "skip")]},
        services,
        engine.trigger,
    )
    assert out["count"] == 1
    assert out["classified"][0]["id"] == "mercari-1"


def test_classify_requires_items(services: Services) -> None:
    engine = _FakeStateEngine()
    with pytest.raises(ValueError):
        handle_classify({}, services, engine.trigger)


def test_listing_list_filters(services: Services) -> None:
    engine = _FakeStateEngine()
    handle_classify(
        {"items": [_item(1, 3000), _item(2, 12000)]},
        services,
        engine.trigger,
    )
    small = handle_listing_list({"priceBand": "small"}, services, engine.trigger)
    assert small["count"] == 1
    assert small["entries"][0]["priceBand"] == "small"
    allof = handle_listing_list({}, services, engine.trigger)
    assert allof["count"] == 2
