"""Phase 7: 統括監視エージェントのテスト（オフライン・dry-run）。"""

from __future__ import annotations

from typing import Any

import pytest

from src.worker.oversight import handle_health
from src.worker.services import Services, build_services
from src.worker.store import LISTING_LIST_SCOPE, LISTINGS_SCOPE


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


def test_health_clean_when_empty(services: Services) -> None:
    engine = _FakeStateEngine()
    out = handle_health({"date": "2026-06-29"}, services, engine.trigger)
    assert out["healthy"] is True
    assert out["anomalies"] == []
    assert out["mode"] == "dry_run"
    assert out["counts"]["drafts"] == 0


def test_health_flags_notify_backlog(services: Services) -> None:
    engine = _FakeStateEngine()
    engine.store[(LISTINGS_SCOPE, "a")] = {
        "sourceListingId": "a",
        "status": "sold",
        "soldOnEbay": True,
        "notified": False,
    }
    out = handle_health({}, services, engine.trigger)
    assert out["healthy"] is False
    assert any("未通知" in a for a in out["anomalies"])
    assert out["counts"]["soldListings"] == 1


def test_health_flags_pipeline_stall(services: Services) -> None:
    engine = _FakeStateEngine()
    engine.store[(LISTING_LIST_SCOPE, "a")] = {"id": "a", "priceBand": "small"}
    out = handle_health({}, services, engine.trigger)
    assert any("下書きが 0 件" in a for a in out["anomalies"])
