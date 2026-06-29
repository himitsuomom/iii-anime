"""分析・仮説検証ループ（M8）。state バック。

`arb::analyze` は出品リスト×成約から消化率レポートを出す。検証枠（全体の約1割）は
`arb::verification-slot` で指定し、`arb::verification-record` で予測と実績を答え合わせする。
独自データとして arb-analysis / arb-verification に蓄積する。
"""

from __future__ import annotations

import math
from datetime import UTC, datetime
from typing import Any

from src.analysis.analyzer import build_report
from src.worker.services import Services
from src.worker.store import (
    ANALYSIS_SCOPE,
    LISTING_LIST_SCOPE,
    LISTINGS_SCOPE,
    VERIFICATION_SCOPE,
    TriggerFn,
    state_get,
    state_list,
    state_set,
)


def _now_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sold_ids(trigger: TriggerFn) -> set[str]:
    listings = [r for r in state_list(trigger, LISTINGS_SCOPE) if isinstance(r, dict)]
    return {str(r.get("sourceListingId", "")) for r in listings if r.get("status") == "sold"}


def handle_analyze(data: dict[str, Any], services: Services, trigger: TriggerFn) -> dict[str, Any]:
    """`arb::analyze` — 消化率レポートを生成し arb-analysis に保存する。"""
    listing_list = [r for r in state_list(trigger, LISTING_LIST_SCOPE) if isinstance(r, dict)]
    report = build_report(listing_list, _sold_ids(trigger))
    report["generatedAt"] = _now_iso()
    state_set(trigger, ANALYSIS_SCOPE, "latest", report)
    return report


def handle_verification_slot(
    data: dict[str, Any], services: Services, trigger: TriggerFn
) -> dict[str, Any]:
    """`arb::verification-slot` — 候補の約1割を検証枠に指定し記録する。

    入力 `{candidateIds: [...], ratio?: 0.1, hypothesis?}`。決定的に等間隔で抽出する。
    """
    candidate_ids = data.get("candidateIds")
    if not isinstance(candidate_ids, list) or not candidate_ids:
        raise ValueError("candidateIds（非空配列）が必要です。")
    ratio = float(data.get("ratio", 0.1))
    hypothesis = str(data.get("hypothesis", "上場した候補は期間内に成約する"))

    n = len(candidate_ids)
    count = max(1, math.ceil(n * ratio))
    step = max(1, n // count)
    selected = [str(candidate_ids[i]) for i in range(0, n, step)][:count]

    for sid in selected:
        state_set(
            trigger,
            VERIFICATION_SCOPE,
            sid,
            {
                "id": sid,
                "status": "testing",
                "hypothesis": hypothesis,
                "prediction": "sell",
                "createdAt": _now_iso(),
            },
        )
    return {"selected": selected, "count": len(selected), "ratio": ratio, "hypothesis": hypothesis}


def handle_verification_record(
    data: dict[str, Any], services: Services, trigger: TriggerFn
) -> dict[str, Any]:
    """`arb::verification-record` — 検証枠の実績を記録し予測と答え合わせする。

    入力 `{id, sold: bool, soldDays?}`。hit = (実績 == 予測 sell)。
    """
    sid = str(data.get("id", "")).strip()
    if not sid:
        raise ValueError("id が必要です。")
    existing = state_get(trigger, VERIFICATION_SCOPE, sid)
    if not isinstance(existing, dict):
        raise ValueError(f"検証枠に未登録の id です: {sid}")

    sold = bool(data.get("sold", False))
    hit = sold is (existing.get("prediction") == "sell")
    record = dict(existing)
    record.update(
        {
            "status": "done",
            "actual": "sold" if sold else "unsold",
            "soldDays": data.get("soldDays"),
            "hit": hit,
            "recordedAt": _now_iso(),
        }
    )
    state_set(trigger, VERIFICATION_SCOPE, sid, record)
    return {"id": sid, "hit": hit, "record": record}


def handle_verification_summary(
    data: dict[str, Any], services: Services, trigger: TriggerFn
) -> dict[str, Any]:
    """`arb::verification-summary` — 検証枠の的中率を集計する。"""
    entries = [r for r in state_list(trigger, VERIFICATION_SCOPE) if isinstance(r, dict)]
    done = [e for e in entries if e.get("status") == "done"]
    hits = sum(1 for e in done if e.get("hit"))
    accuracy = round(hits / len(done), 4) if done else 0.0
    return {
        "total": len(entries),
        "completed": len(done),
        "hits": hits,
        "accuracy": accuracy,
    }
