"""Phase 5: 分析・仮説検証のテスト（オフライン）。"""

from __future__ import annotations

from typing import Any

import pytest

from src.analysis.analyzer import build_report
from src.worker.analysis import (
    handle_analyze,
    handle_verification_record,
    handle_verification_slot,
    handle_verification_summary,
)
from src.worker.services import Services, build_services
from src.worker.store import ANALYSIS_SCOPE, LISTING_LIST_SCOPE, LISTINGS_SCOPE


class _FakeStateEngine:
    def __init__(self) -> None:
        self.store: dict[tuple[str, str], Any] = {}

    def trigger(self, req: dict[str, Any]) -> Any:
        fid = req["function_id"]
        p = req.get("payload", {})
        if fid == "state::set":
            self.store[(p["scope"], p["key"])] = p["value"]
            return {"new_value": p["value"]}
        if fid == "state::get":
            return self.store.get((p["scope"], p["key"]))
        if fid == "state::list":
            return [v for (s, _), v in self.store.items() if s == p["scope"]]
        raise AssertionError(fid)


@pytest.fixture
def services() -> Services:
    return build_services(force_offline=True, dry_run=True)


def test_build_report_sell_through() -> None:
    listing_list = [
        {"id": "a", "priceBand": "small", "marketplace": "mercari", "category": "x"},
        {"id": "b", "priceBand": "small", "marketplace": "mercari", "category": "x"},
        {"id": "c", "priceBand": "large", "marketplace": "yahoo_auctions", "category": "y"},
    ]
    report = build_report(listing_list, sold_ids={"a", "c"})
    assert report["total"] == 3
    assert report["sold"] == 2
    assert report["byBand"]["small"]["sellThrough"] == 0.5
    assert report["byBand"]["large"]["sellThrough"] == 1.0
    assert report["bestBand"] == "large"


def _seed(engine: _FakeStateEngine) -> None:
    engine.store[(LISTING_LIST_SCOPE, "a")] = {"id": "a", "priceBand": "small", "marketplace": "mercari", "category": "x"}
    engine.store[(LISTING_LIST_SCOPE, "b")] = {"id": "b", "priceBand": "small", "marketplace": "mercari", "category": "x"}
    engine.store[(LISTINGS_SCOPE, "a")] = {"sourceListingId": "a", "status": "sold"}
    engine.store[(LISTINGS_SCOPE, "b")] = {"sourceListingId": "b", "status": "draft"}


def test_analyze_persists_report(services: Services) -> None:
    engine = _FakeStateEngine()
    _seed(engine)
    report = handle_analyze({}, services, engine.trigger)
    assert report["sold"] == 1
    assert report["total"] == 2
    assert engine.store[(ANALYSIS_SCOPE, "latest")]["sold"] == 1


def test_verification_slot_selects_tenth(services: Services) -> None:
    engine = _FakeStateEngine()
    ids = [f"id-{i}" for i in range(10)]
    out = handle_verification_slot({"candidateIds": ids, "ratio": 0.1}, services, engine.trigger)
    assert out["count"] == 1  # ceil(10 * 0.1) == 1


def test_verification_slot_requires_candidates(services: Services) -> None:
    engine = _FakeStateEngine()
    with pytest.raises(ValueError):
        handle_verification_slot({"candidateIds": []}, services, engine.trigger)


def test_verification_record_and_summary(services: Services) -> None:
    engine = _FakeStateEngine()
    ids = [f"id-{i}" for i in range(20)]
    slot = handle_verification_slot({"candidateIds": ids, "ratio": 0.1}, services, engine.trigger)
    assert slot["count"] == 2
    sel = slot["selected"]
    # 1件は成約（予測 sell 的中）、1件は未成約（外れ）。
    handle_verification_record({"id": sel[0], "sold": True, "soldDays": 5}, services, engine.trigger)
    handle_verification_record({"id": sel[1], "sold": False}, services, engine.trigger)
    summary = handle_verification_summary({}, services, engine.trigger)
    assert summary["completed"] == 2
    assert summary["hits"] == 1
    assert summary["accuracy"] == 0.5


def test_verification_record_unknown_id(services: Services) -> None:
    engine = _FakeStateEngine()
    with pytest.raises(ValueError):
        handle_verification_record({"id": "nope", "sold": True}, services, engine.trigger)
