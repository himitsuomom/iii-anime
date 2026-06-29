"""販売監視・在庫同期・日次記録（M6）。state バック。

成約検知は、ライブでは後フェーズの eBay ポーラが arb-listings の `soldOnEbay` を立てる。
Phase 0/4 では `arb::mark-sold` がそれを担う（webhook/poll の代理）。`arb::monitor-sales` は
未通知の成約を拾い、**仕入れ元 URL 付き**で Telegram 通知し（dry-run 安全）、売上を古物台帳へ
記録する。二重販売防止: 成約済みは status!=cancelled なので再下書きされない。
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from src.worker.services import Services
from src.worker.store import (
    DAILY_SCOPE,
    DRAFTS_SCOPE,
    LEDGER_SCOPE,
    LISTING_LIST_SCOPE,
    LISTINGS_SCOPE,
    TriggerFn,
    state_list,
    state_set,
    update_listing,
)


def _now_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def handle_mark_sold(data: dict[str, Any], services: Services, trigger: TriggerFn) -> dict[str, Any]:
    """`arb::mark-sold` — 出品が成約したと記録する（eBay webhook/poll の代理）。"""
    source_listing_id = str(data.get("sourceListingId", "")).strip()
    if not source_listing_id:
        raise ValueError("sourceListingId が必要です。")
    record = update_listing(
        trigger,
        source_listing_id,
        soldOnEbay=True,
        status="sold",
        soldAt=str(data.get("soldAt") or _now_iso()),
    )
    return {"ok": True, "record": record}


def handle_monitor_sales(
    data: dict[str, Any], services: Services, trigger: TriggerFn
) -> dict[str, Any]:
    """`arb::monitor-sales` — 未通知の成約を通知し売上を台帳へ記録する（cron 30分）。

    仕入れ元 URL 付きで Telegram 通知（dry-run なら preview のみ）。冪等: notified=True で二重通知防止。
    """
    listings = [r for r in state_list(trigger, LISTINGS_SCOPE) if isinstance(r, dict)]
    notified: list[dict[str, Any]] = []
    active = 0
    sold = 0

    for rec in listings:
        status = rec.get("status")
        if status == "sold":
            sold += 1
        elif status != "cancelled":
            active += 1

        if rec.get("soldOnEbay") and not rec.get("notified"):
            sid = str(rec.get("sourceListingId", ""))
            url = rec.get("url")
            title = rec.get("title", sid)
            services.notifier.send(
                f"🟢 売れました: {title}（仕入れて発送してください）",
                source_url=url if url else None,
            )
            update_listing(trigger, sid, notified=True)
            # 売上を古物台帳へ（数量1・金額は後で確定するため 0 プレースホルダ）。
            entry_id = f"sale-{sid}"
            state_set(
                trigger,
                LEDGER_SCOPE,
                entry_id,
                {
                    "id": entry_id,
                    "transactionType": "sale",
                    "itemDescription": str(title),
                    "quantity": 1,
                    "amount": {"amount": 0, "currency": "JPY"},
                    "sourceUrl": url,
                    "occurredAt": str(rec.get("soldAt") or _now_iso()),
                    "recordedAt": _now_iso(),
                },
            )
            notified.append({"sourceListingId": sid, "url": url})

    return {
        "notifiedCount": len(notified),
        "notified": notified,
        "activeCount": active,
        "soldCount": sold,
        "dryRun": services.dry_run,
    }


def handle_daily_record(
    data: dict[str, Any], services: Services, trigger: TriggerFn
) -> dict[str, Any]:
    """`arb::daily-record` — 日次 KPI スナップショットを arb-daily に記録する（cron 日次）。"""
    date = str(data.get("date") or _now_iso()[:10])
    listing_list = [r for r in state_list(trigger, LISTING_LIST_SCOPE) if isinstance(r, dict)]
    drafts = [r for r in state_list(trigger, DRAFTS_SCOPE) if isinstance(r, dict)]
    listings = [r for r in state_list(trigger, LISTINGS_SCOPE) if isinstance(r, dict)]

    sold = sum(1 for r in listings if r.get("status") == "sold")
    active = sum(1 for r in listings if r.get("status") not in ("sold", "cancelled"))
    by_band: dict[str, int] = {}
    for r in listing_list:
        band = str(r.get("priceBand", "unknown"))
        by_band[band] = by_band.get(band, 0) + 1

    record = {
        "date": date,
        "listingListCount": len(listing_list),
        "draftCount": len(drafts),
        "activeListings": active,
        "soldListings": sold,
        "byBand": by_band,
        "recordedAt": _now_iso(),
    }
    state_set(trigger, DAILY_SCOPE, date, record)
    return record
