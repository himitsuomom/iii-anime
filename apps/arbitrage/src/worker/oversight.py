"""統括監視エージェント（M11/Phase 7）。state バック。

各サブシステムの状態を集計し、日次の健全性サマリと異常アラートを出す。異常時は Telegram で
通知（dry_run なら preview のみ）。cron で日次実行する。
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from src.worker.services import Services
from src.worker.store import (
    ANALYSIS_SCOPE,
    CANDIDATES_SCOPE,
    DAILY_SCOPE,
    DRAFTS_SCOPE,
    LEDGER_SCOPE,
    LISTING_LIST_SCOPE,
    LISTINGS_SCOPE,
    SHIPMENTS_SCOPE,
    VERIFICATION_SCOPE,
    TriggerFn,
    state_list,
)


def _now_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _count(trigger: TriggerFn, scope: str) -> int:
    return len([r for r in state_list(trigger, scope) if isinstance(r, dict)])


def handle_health(data: dict[str, Any], services: Services, trigger: TriggerFn) -> dict[str, Any]:
    """`arb::health` — システム健全性を要約し、異常があれば通知する。"""
    listings = [r for r in state_list(trigger, LISTINGS_SCOPE) if isinstance(r, dict)]
    listing_list = [r for r in state_list(trigger, LISTING_LIST_SCOPE) if isinstance(r, dict)]
    drafts = [r for r in state_list(trigger, DRAFTS_SCOPE) if isinstance(r, dict)]
    verification = [r for r in state_list(trigger, VERIFICATION_SCOPE) if isinstance(r, dict)]

    sold = sum(1 for r in listings if r.get("status") == "sold")
    active = sum(1 for r in listings if r.get("status") not in ("sold", "cancelled"))
    notify_backlog = sum(1 for r in listings if r.get("soldOnEbay") and not r.get("notified"))

    done_verifications = [v for v in verification if v.get("status") == "done"]
    hits = sum(1 for v in done_verifications if v.get("hit"))
    accuracy = round(hits / len(done_verifications), 4) if done_verifications else None

    counts = {
        "candidates": _count(trigger, CANDIDATES_SCOPE),
        "listingList": len(listing_list),
        "drafts": len(drafts),
        "activeListings": active,
        "soldListings": sold,
        "ledgerEntries": _count(trigger, LEDGER_SCOPE),
        "verifications": len(verification),
        "shipments": _count(trigger, SHIPMENTS_SCOPE),
        "analysisRuns": _count(trigger, ANALYSIS_SCOPE),
        "dailyRecords": _count(trigger, DAILY_SCOPE),
    }

    anomalies: list[str] = []
    if notify_backlog > 0:
        anomalies.append(f"成約済みで未通知が {notify_backlog} 件（monitor-sales 要確認）")
    if len(listing_list) > 0 and len(drafts) == 0:
        anomalies.append("出品リストに候補があるが下書きが 0 件（パイプライン停滞の可能性）")
    if accuracy is not None and len(done_verifications) >= 5 and accuracy < 0.5:
        anomalies.append(f"検証枠の的中率が低い（{accuracy}）— 仮説の見直しを推奨")

    summary = {
        "date": str(data.get("date") or _now_iso()[:10]),
        "mode": "dry_run" if services.dry_run else "live",
        "researchLive": services.research_live,
        "counts": counts,
        "verificationAccuracy": accuracy,
        "anomalies": anomalies,
        "healthy": not anomalies,
        "generatedAt": _now_iso(),
    }

    # 異常があれば通知（dry_run なら preview のみ）。
    if anomalies:
        services.notifier.send("⚠️ 越境転売システム異常: " + " / ".join(anomalies))

    return summary
