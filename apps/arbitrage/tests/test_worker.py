"""state バックのハンドラと登録配線のテスト（in-memory fake trigger）。"""

from __future__ import annotations

from typing import Any

import pytest

from src.worker.app import register_arbitrage_functions, registered_function_ids
from src.worker.handlers import handle_draft_listing
from src.worker.services import Services, build_services
from src.worker.store import (
    DRAFTS_SCOPE,
    LEDGER_SCOPE,
    LISTINGS_SCOPE,
    handle_ledger_list,
    handle_ledger_record,
)


class _FakeStateEngine:
    """state::set/get/list を in-memory で模した fake trigger（EC のパターン流用）。"""

    def __init__(self) -> None:
        self.store: dict[tuple[str, str], Any] = {}

    def trigger(self, req: dict[str, Any]) -> Any:
        fid = req["function_id"]
        payload = req.get("payload", {})
        if fid == "state::set":
            self.store[(payload["scope"], payload["key"])] = payload["value"]
            return {"new_value": payload["value"]}
        if fid == "state::get":
            return self.store.get((payload["scope"], payload["key"]))
        if fid == "state::list":
            scope = payload["scope"]
            return [v for (s, _), v in self.store.items() if s == scope]
        raise AssertionError(f"unexpected function_id {fid}")


@pytest.fixture
def services() -> Services:
    return build_services(force_offline=True, dry_run=True)


def _source(idx: int = 0) -> dict[str, Any]:
    return {
        "id": f"snkrdunk-{idx}",
        "marketplace": "snkrdunk",
        "url": f"https://x.invalid/i/{idx}",
        "title": "rare sneaker",
        "price": {"amount": 8000, "currency": "JPY"},
        "fetchedAt": "2026-06-29T00:00:00Z",
        "condition": "美品",
    }


def test_draft_listing_persists_and_marks_inventory(services: Services) -> None:
    engine = _FakeStateEngine()
    out = handle_draft_listing(
        {"sourceListing": _source(1), "priceUsd": {"amount": 20000, "currency": "USD"}, "now": "t"},
        services,
        engine.trigger,
    )
    assert out["skipped"] is False
    assert out["draft"]["mode"] == "dry_run"
    assert out["draft"]["status"] == "draft"
    # draft と在庫同期レコードが state に入る。
    assert engine.store[(DRAFTS_SCOPE, "draft-snkrdunk-1")]["sourceListingId"] == "snkrdunk-1"
    assert engine.store[(LISTINGS_SCOPE, "snkrdunk-1")]["status"] == "draft"


def test_draft_listing_skips_duplicate(services: Services) -> None:
    """二重販売防止: 同一仕入れ品の再下書きはスキップする。"""
    engine = _FakeStateEngine()
    payload = {"sourceListing": _source(2), "priceUsd": {"amount": 20000, "currency": "USD"}, "now": "t"}
    first = handle_draft_listing(payload, services, engine.trigger)
    assert first["skipped"] is False
    second = handle_draft_listing(payload, services, engine.trigger)
    assert second["skipped"] is True
    assert "二重販売防止" in second["reason"]


def test_ledger_record_and_list() -> None:
    engine = _FakeStateEngine()
    entry = {
        "id": "led-1",
        "transactionType": "purchase",
        "itemDescription": "rare sneaker",
        "quantity": 1,
        "amount": {"amount": 8000, "currency": "JPY"},
        "occurredAt": "2026-06-29T00:00:00Z",
        "recordedAt": "2026-06-29T00:00:00Z",
        "counterpartyName": "seller-2",
    }
    rec = handle_ledger_record(entry, engine.trigger)
    assert rec == {"ok": True, "id": "led-1"}
    assert engine.store[(LEDGER_SCOPE, "led-1")]["transactionType"] == "purchase"

    listed = handle_ledger_list({}, engine.trigger)
    assert listed["count"] == 1
    # 種別フィルタ。
    assert handle_ledger_list({"transactionType": "sale"}, engine.trigger)["count"] == 0


def test_ledger_record_requires_id() -> None:
    engine = _FakeStateEngine()
    with pytest.raises(ValueError):
        handle_ledger_record({"transactionType": "purchase"}, engine.trigger)


class _FakeRegisterEngine:
    """register_function / register_trigger / trigger を記録する fake。"""

    def __init__(self) -> None:
        self.functions: dict[str, Any] = {}
        self.triggers: list[dict[str, Any]] = []

    def register_function(self, function_id: str, handler: Any) -> None:
        self.functions[function_id] = handler

    def register_trigger(self, trigger: dict[str, Any]) -> None:
        self.triggers.append(trigger)

    def trigger(self, req: dict[str, Any]) -> Any:
        return None


def test_registration_wires_all_functions(services: Services) -> None:
    engine = _FakeRegisterEngine()
    register_arbitrage_functions(engine, services)
    for fid in registered_function_ids():
        assert fid in engine.functions
    # 各関数に HTTP トリガーが付く（cron トリガーが追加で乗るため >= で確認）。
    http_triggers = [t for t in engine.triggers if t.get("type") == "http"]
    assert len(http_triggers) == len(registered_function_ids())
    paths = {t["config"]["api_path"] for t in http_triggers}
    assert "/arb/source/scan" in paths
    assert "/arb/ledger/record" in paths
    assert "/arb/monitor-sales" in paths
    # cron トリガーが monitor-sales / daily-record に登録される。
    cron = [t for t in engine.triggers if t.get("type") == "cron"]
    assert {t["function_id"] for t in cron} == {"arb::monitor-sales", "arb::daily-record"}
