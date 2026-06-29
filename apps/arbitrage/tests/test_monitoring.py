"""Phase 4: 販売監視・在庫同期・日次記録のテスト（オフライン・dry-run）。"""

from __future__ import annotations

from typing import Any

import pytest

from src.worker.handlers import handle_draft_listing
from src.worker.monitoring import handle_daily_record, handle_mark_sold, handle_monitor_sales
from src.worker.services import Services, build_services
from src.worker.store import DAILY_SCOPE, LEDGER_SCOPE


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


def _draft(engine: _FakeStateEngine, services: Services, idx: int) -> None:
    handle_draft_listing(
        {
            "sourceListing": {
                "id": f"mercari-{idx}",
                "marketplace": "mercari",
                "url": f"https://x.invalid/{idx}",
                "title": f"item {idx}",
                "price": {"amount": 8000, "currency": "JPY"},
                "fetchedAt": "2026-06-29T00:00:00Z",
            },
            "priceUsd": {"amount": 20000, "currency": "USD"},
            "now": "t",
        },
        services,
        engine.trigger,
    )


def test_mark_sold_sets_flags(services: Services) -> None:
    engine = _FakeStateEngine()
    _draft(engine, services, 1)
    out = handle_mark_sold({"sourceListingId": "mercari-1"}, services, engine.trigger)
    assert out["record"]["soldOnEbay"] is True
    assert out["record"]["status"] == "sold"
    # url/title が下書き時に保持されている。
    assert out["record"]["url"] == "https://x.invalid/1"


def test_mark_sold_requires_id(services: Services) -> None:
    engine = _FakeStateEngine()
    with pytest.raises(ValueError):
        handle_mark_sold({}, services, engine.trigger)


def test_monitor_notifies_once_and_records_sale(services: Services) -> None:
    engine = _FakeStateEngine()
    _draft(engine, services, 1)
    _draft(engine, services, 2)
    handle_mark_sold({"sourceListingId": "mercari-1"}, services, engine.trigger)

    first = handle_monitor_sales({}, services, engine.trigger)
    assert first["notifiedCount"] == 1
    assert first["soldCount"] == 1
    assert first["activeCount"] == 1
    assert first["dryRun"] is True
    # 売上が古物台帳に記録される。
    assert ("kobutsu-ledger" == LEDGER_SCOPE)
    assert engine.store[(LEDGER_SCOPE, "sale-mercari-1")]["transactionType"] == "sale"

    # 冪等: 二度目は通知 0（notified=True）。
    second = handle_monitor_sales({}, services, engine.trigger)
    assert second["notifiedCount"] == 0


def test_daily_record_snapshot(services: Services) -> None:
    engine = _FakeStateEngine()
    _draft(engine, services, 1)
    handle_mark_sold({"sourceListingId": "mercari-1"}, services, engine.trigger)
    rec = handle_daily_record({"date": "2026-06-29"}, services, engine.trigger)
    assert rec["date"] == "2026-06-29"
    assert rec["soldListings"] == 1
    assert rec["draftCount"] == 1
    assert engine.store[(DAILY_SCOPE, "2026-06-29")]["soldListings"] == 1
