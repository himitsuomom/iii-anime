"""売れ筋要因分析（M8）。純関数・副作用なし。

出品リスト（価格帯/PF/カテゴリ）と成約状況を突き合わせ、sell-through（消化率）を
全体・価格帯別・PF別に出す。相関を因果と断定しない方針のため、件数（サンプル数）も併記する。
"""

from __future__ import annotations

from typing import Any


def _rate(sold: int, total: int) -> float:
    return round(sold / total, 4) if total > 0 else 0.0


def group_performance(
    listing_list: list[dict[str, Any]], sold_ids: set[str], key: str
) -> dict[str, dict[str, Any]]:
    """listing_list を key（priceBand / marketplace / category）で集計し消化率を返す。"""
    buckets: dict[str, dict[str, Any]] = {}
    for entry in listing_list:
        group = str(entry.get(key, "unknown"))
        b = buckets.setdefault(group, {"total": 0, "sold": 0})
        b["total"] += 1
        if str(entry.get("id", "")) in sold_ids:
            b["sold"] += 1
    for b in buckets.values():
        b["sellThrough"] = _rate(b["sold"], b["total"])
    return buckets


def build_report(
    listing_list: list[dict[str, Any]], sold_ids: set[str]
) -> dict[str, Any]:
    """全体・価格帯別・PF別・カテゴリ別の消化率レポートを組み立てる。"""
    total = len(listing_list)
    sold = sum(1 for e in listing_list if str(e.get("id", "")) in sold_ids)
    by_band = group_performance(listing_list, sold_ids, "priceBand")
    by_marketplace = group_performance(listing_list, sold_ids, "marketplace")
    by_category = group_performance(listing_list, sold_ids, "category")

    # 最も消化率の高い価格帯（サンプル1件以上）。断定せず指標として提示。
    ranked_bands = sorted(
        (g for g in by_band.items() if g[1]["total"] > 0),
        key=lambda kv: kv[1]["sellThrough"],
        reverse=True,
    )
    best_band = ranked_bands[0][0] if ranked_bands else None

    return {
        "total": total,
        "sold": sold,
        "sellThrough": _rate(sold, total),
        "byBand": by_band,
        "byMarketplace": by_marketplace,
        "byCategory": by_category,
        "bestBand": best_band,
        "sampleNote": "件数が少ない群は参考値（相関≠因果）",
    }
