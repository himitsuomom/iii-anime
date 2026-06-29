"""state バックの永続化（古物台帳 / 在庫同期）。

iii-state を scope/key で**冪等 upsert**する（EC store.py と同じ非競合パターン）。
`trigger` は iii.trigger 互換で注入され、エンジン非依存にテストできる。

スコープ:
  - `kobutsu-ledger`  : 古物台帳エントリ（id キー）
  - `arb-listings`    : 在庫同期 / 二重販売防止（sourceListingId キー）
  - `arb-candidates`  : 仕入れ候補（id キー）
  - `arb-drafts`      : 出品下書き（draftId キー）
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from src.worker.serializers import ledger_from_dict, ledger_to_dict

# iii.trigger 互換: {"function_id", "payload"} を受け取り結果を返す。
TriggerFn = Callable[[dict[str, Any]], Any]

LEDGER_SCOPE = "kobutsu-ledger"
LISTINGS_SCOPE = "arb-listings"
CANDIDATES_SCOPE = "arb-candidates"
DRAFTS_SCOPE = "arb-drafts"


def state_set(trigger: TriggerFn, scope: str, key: str, value: dict[str, Any]) -> None:
    trigger({"function_id": "state::set", "payload": {"scope": scope, "key": key, "value": value}})


def state_get(trigger: TriggerFn, scope: str, key: str) -> Any:
    return trigger({"function_id": "state::get", "payload": {"scope": scope, "key": key}})


def state_list(trigger: TriggerFn, scope: str) -> list[Any]:
    return trigger({"function_id": "state::list", "payload": {"scope": scope}}) or []


# ── 古物台帳 (M11) ──
def handle_ledger_record(data: dict[str, Any], trigger: TriggerFn) -> dict[str, Any]:
    """`ledger::record` — 古物台帳エントリを id キーで冪等 upsert する。"""
    entry = ledger_to_dict(ledger_from_dict(data))
    state_set(trigger, LEDGER_SCOPE, entry["id"], entry)
    return {"ok": True, "id": entry["id"]}


def handle_ledger_list(data: dict[str, Any], trigger: TriggerFn) -> dict[str, Any]:
    """`ledger::list` — 全台帳エントリを返す（任意で transactionType で絞り込み）。"""
    entries = [e for e in state_list(trigger, LEDGER_SCOPE) if isinstance(e, dict)]
    tx_type = data.get("transactionType")
    if tx_type:
        entries = [e for e in entries if e.get("transactionType") == tx_type]
    return {"entries": entries, "count": len(entries)}


# ── 在庫同期 / 二重販売防止 (M6 前段) ──
def active_listing_for_source(trigger: TriggerFn, source_listing_id: str) -> dict[str, Any] | None:
    """同一仕入れ品に対する有効な出品が既にあれば返す（二重出品検知）。

    一点物の中古品を複数回スキャンしても二重出品しないためのガード。`cancelled` は無視。
    """
    record = state_get(trigger, LISTINGS_SCOPE, source_listing_id)
    if isinstance(record, dict) and record.get("status") != "cancelled":
        return record
    return None


def mark_listing(
    trigger: TriggerFn,
    *,
    source_listing_id: str,
    draft_id: str,
    status: str,
    sold_on_ebay: bool = False,
) -> dict[str, Any]:
    """在庫同期レコードを upsert する（出品〜成約のライフサイクルを追跡）。"""
    record = {
        "sourceListingId": source_listing_id,
        "draftId": draft_id,
        "status": status,
        "soldOnEbay": sold_on_ebay,
    }
    state_set(trigger, LISTINGS_SCOPE, source_listing_id, record)
    return record
