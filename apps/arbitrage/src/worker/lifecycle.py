"""出品ライフサイクル: 承認・自動投稿・最適化（M7/M9）。state バック。

human-in-the-loop: `arb::approve-draft` が人間の承認（draft→ready）を表す。自動投稿
`arb::publish-listing` は **mode=auto かつ status=ready** のときだけ実投稿に進み、dry_run の間は
preview に留める（凍結回避・§1-2）。`arb::optimize` は売れ残り入替候補を経過日数で抽出し、
価格自動追従には最低利益ラインのガードを文書化する（§9-9）。
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from src.worker.services import Services
from src.worker.store import (
    DRAFTS_SCOPE,
    LISTING_LIST_SCOPE,
    LISTINGS_SCOPE,
    TriggerFn,
    state_get,
    state_list,
    state_set,
    update_listing,
)


def _now() -> datetime:
    return datetime.now(UTC)


def _now_iso() -> str:
    return _now().strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_iso(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def handle_approve_draft(
    data: dict[str, Any], services: Services, trigger: TriggerFn
) -> dict[str, Any]:
    """`arb::approve-draft` — 人間の承認で draft→ready に上げる（任意で mode を指定）。"""
    draft_id = str(data.get("draftId", "")).strip()
    if not draft_id:
        raise ValueError("draftId が必要です。")
    draft = state_get(trigger, DRAFTS_SCOPE, draft_id)
    if not isinstance(draft, dict):
        raise ValueError(f"未登録の draftId です: {draft_id}")

    mode = str(data.get("mode", draft.get("mode", "human_review")))
    if mode not in ("dry_run", "human_review", "auto"):
        raise ValueError(f"不正な mode: {mode}")
    updated = dict(draft)
    updated["status"] = "ready"
    updated["mode"] = mode
    state_set(trigger, DRAFTS_SCOPE, draft_id, updated)
    update_listing(trigger, str(draft.get("sourceListingId", "")), status="ready")
    return {"ok": True, "draftId": draft_id, "status": "ready", "mode": mode}


def handle_publish_listing(
    data: dict[str, Any], services: Services, trigger: TriggerFn
) -> dict[str, Any]:
    """`arb::publish-listing` — mode=auto かつ status=ready の下書きのみ投稿に進む。

    dry_run の間は実投稿せず preview を返す（凍結回避）。実投稿の eBay API 呼び出しは
    認証情報を伴う後段の統合点（ここではゲートと state 遷移のみ実装）。
    """
    draft_id = str(data.get("draftId", "")).strip()
    if not draft_id:
        raise ValueError("draftId が必要です。")
    draft = state_get(trigger, DRAFTS_SCOPE, draft_id)
    if not isinstance(draft, dict):
        raise ValueError(f"未登録の draftId です: {draft_id}")

    if draft.get("mode") != "auto" or draft.get("status") != "ready":
        return {
            "published": False,
            "reason": "mode=auto かつ status=ready のみ自動投稿可能（現在: "
            f"mode={draft.get('mode')}, status={draft.get('status')}）",
        }
    if services.dry_run:
        return {"published": False, "dryRun": True, "preview": draft}

    # LIVE: 実 eBay 投稿は後段統合（要 EBAY_OAUTH_TOKEN）。ここでは状態のみ published に。
    updated = dict(draft)
    updated["status"] = "published"
    state_set(trigger, DRAFTS_SCOPE, draft_id, updated)
    update_listing(trigger, str(draft.get("sourceListingId", "")), status="published")
    return {"published": True, "draftId": draft_id}


def handle_optimize(data: dict[str, Any], services: Services, trigger: TriggerFn) -> dict[str, Any]:
    """`arb::optimize` — 経過日数で売れ残り入替候補を抽出する（小中45日/大75日）。

    入力 `{now?}`（ISO, テスト用）。価格自動追従は最低利益ラインを守る前提（本フェーズは
    候補抽出のみ・自動値下げはしない）。
    """
    now = _parse_iso(data.get("now")) or _now()
    cfg = services.settings.optimize

    bands: dict[str, str] = {
        str(e.get("id")): str(e.get("priceBand", "medium"))
        for e in state_list(trigger, LISTING_LIST_SCOPE)
        if isinstance(e, dict)
    }

    candidates: list[dict[str, Any]] = []
    for rec in state_list(trigger, LISTINGS_SCOPE):
        if not isinstance(rec, dict):
            continue
        if rec.get("status") in ("sold", "cancelled"):
            continue
        listed = _parse_iso(rec.get("listedAt"))
        if listed is None:
            continue
        age_days = (now - listed).days
        sid = str(rec.get("sourceListingId", ""))
        band = bands.get(sid, "medium")
        threshold = (
            cfg.restock_days_large if band == "large" else cfg.restock_days_small_medium
        )
        if age_days >= threshold:
            candidates.append(
                {
                    "sourceListingId": sid,
                    "priceBand": band,
                    "ageDays": age_days,
                    "threshold": threshold,
                }
            )

    return {"restockCandidates": candidates, "count": len(candidates), "asOf": now.strftime("%Y-%m-%dT%H:%M:%SZ")}
