"""Phase 6: 承認・自動投稿ゲート・最適化・発送QR・台帳CSV/集計（オフライン・dry-run）。"""

from __future__ import annotations

from typing import Any

import pytest

from src.ledger.export import summarize, to_csv
from src.worker.fulfillment import handle_shipment_qr
from src.worker.handlers import handle_draft_listing
from src.worker.lifecycle import (
    handle_approve_draft,
    handle_optimize,
    handle_publish_listing,
)
from src.worker.services import Services, build_services
from src.worker.store import (
    LISTING_LIST_SCOPE,
    SHIPMENTS_SCOPE,
    handle_ledger_export,
    handle_ledger_record,
    handle_ledger_stats,
)


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
def services_dry() -> Services:
    return build_services(force_offline=True, dry_run=True)


@pytest.fixture
def services_live() -> Services:
    return build_services(force_offline=True, dry_run=False)


def _draft(engine: _FakeStateEngine, services: Services, idx: int = 1, now: str = "2026-05-01T00:00:00Z") -> str:
    out = handle_draft_listing(
        {
            "sourceListing": {
                "id": f"mercari-{idx}",
                "marketplace": "mercari",
                "url": f"https://x.invalid/{idx}",
                "title": "item",
                "price": {"amount": 8000, "currency": "JPY"},
                "fetchedAt": "2026-05-01T00:00:00Z",
            },
            "priceUsd": {"amount": 20000, "currency": "USD"},
            "now": now,
        },
        services,
        engine.trigger,
    )
    return out["draft"]["draftId"]


def test_approve_then_publish_gating(services_dry: Services, services_live: Services) -> None:
    engine = _FakeStateEngine()
    draft_id = _draft(engine, services_dry)

    blocked = handle_publish_listing({"draftId": draft_id}, services_live, engine.trigger)
    assert blocked["published"] is False

    handle_approve_draft({"draftId": draft_id, "mode": "auto"}, services_dry, engine.trigger)

    dry = handle_publish_listing({"draftId": draft_id}, services_dry, engine.trigger)
    assert dry["published"] is False
    assert dry["dryRun"] is True

    live = handle_publish_listing({"draftId": draft_id}, services_live, engine.trigger)
    assert live["published"] is True


def test_approve_requires_known_draft(services_dry: Services) -> None:
    engine = _FakeStateEngine()
    with pytest.raises(ValueError):
        handle_approve_draft({"draftId": "nope"}, services_dry, engine.trigger)


def test_optimize_flags_stale_listings(services_dry: Services) -> None:
    engine = _FakeStateEngine()
    _draft(engine, services_dry, idx=1, now="2026-01-01T00:00:00Z")
    engine.store[(LISTING_LIST_SCOPE, "mercari-1")] = {"id": "mercari-1", "priceBand": "small"}
    out = handle_optimize({"now": "2026-06-01T00:00:00Z"}, services_dry, engine.trigger)
    assert out["count"] == 1
    assert out["restockCandidates"][0]["priceBand"] == "small"


def test_optimize_skips_fresh(services_dry: Services) -> None:
    engine = _FakeStateEngine()
    _draft(engine, services_dry, idx=2, now="2026-05-28T00:00:00Z")
    out = handle_optimize({"now": "2026-06-01T00:00:00Z"}, services_dry, engine.trigger)
    assert out["count"] == 0


def test_shipment_qr_dry_run(services_dry: Services) -> None:
    engine = _FakeStateEngine()
    out = handle_shipment_qr({"orderId": "ORD-1", "service": "ems"}, services_dry, engine.trigger)
    assert out["carrier"] == "japan_post"
    assert out["service"] == "ems"
    assert out["dryRun"] is True
    assert engine.store[(SHIPMENTS_SCOPE, "ship-ORD-1")]["orderId"] == "ORD-1"


def test_shipment_qr_requires_order(services_dry: Services) -> None:
    engine = _FakeStateEngine()
    with pytest.raises(ValueError):
        handle_shipment_qr({}, services_dry, engine.trigger)


def test_to_csv_and_summarize() -> None:
    entries = [
        {"id": "p1", "transactionType": "purchase", "amount": {"amount": 8000, "currency": "JPY"}, "quantity": 1},
        {"id": "s1", "transactionType": "sale", "amount": {"amount": 20000, "currency": "JPY"}, "quantity": 1},
    ]
    csv_text = to_csv(entries)
    assert "id,transactionType" in csv_text.splitlines()[0]
    assert "p1,purchase" in csv_text
    stats = summarize(entries)
    assert stats == {
        "purchaseCount": 1,
        "saleCount": 1,
        "purchaseTotalJpy": 8000,
        "saleTotalJpy": 20000,
        "grossMarginJpy": 12000,
    }


def test_ledger_export_and_stats_handlers() -> None:
    engine = _FakeStateEngine()
    handle_ledger_record(
        {
            "id": "p1",
            "transactionType": "purchase",
            "itemDescription": "x",
            "quantity": 1,
            "amount": {"amount": 8000, "currency": "JPY"},
            "occurredAt": "2026-06-01T00:00:00Z",
            "recordedAt": "2026-06-01T00:00:00Z",
        },
        engine.trigger,
    )
    export = handle_ledger_export({}, engine.trigger)
    assert export["rowCount"] == 1
    assert "p1,purchase" in export["csv"]
    stats = handle_ledger_stats({}, engine.trigger)
    assert stats["purchaseTotalJpy"] == 8000
