#!/usr/bin/env python3
"""価格・需要分析スクリプト。
使い方: python scripts/run_analytics.py
API不要 — サンプルデータでローカル完結。
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.analytics.demand_analyzer import DemandAnalyzer
from src.analytics.price_tracker import DemandSignal, PricePoint, PriceTracker

# ---- サンプルデータ ----

SAMPLE_PRICES = [
    PricePoint(product_id="mug-001", platform="shopify", price=24.99, currency="USD"),
    PricePoint(product_id="mug-001", platform="etsy",    price=22.50, currency="USD"),
    PricePoint(product_id="mug-001", platform="amazon",  price=19.99, currency="USD"),
    PricePoint(product_id="tshirt-001", platform="shopify", price=29.99, currency="USD"),
    PricePoint(product_id="tshirt-001", platform="etsy",    price=27.00, currency="USD"),
]

SAMPLE_SIGNALS = [
    DemandSignal(keyword="hiking mug",         search_volume_estimate=8500,  trend_score=0.78, platform="shopify"),
    DemandSignal(keyword="hiking mug",         search_volume_estimate=9200,  trend_score=0.82, platform="etsy"),
    DemandSignal(keyword="mountain lover gift",search_volume_estimate=3200,  trend_score=0.65, platform="etsy"),
    DemandSignal(keyword="mountain lover gift",search_volume_estimate=2800,  trend_score=0.70, platform="shopify"),
    DemandSignal(keyword="cat notebook",       search_volume_estimate=15000, trend_score=0.55, platform="etsy"),
    DemandSignal(keyword="kawaii stationery",  search_volume_estimate=500,   trend_score=0.45, platform="etsy"),
    DemandSignal(keyword="nature coffee mug",  search_volume_estimate=6000,  trend_score=0.72, platform="shopify"),
]

SAMPLE_COST = 8.50
TARGET_MARGIN = 0.35
KEYWORDS = ["hiking mug", "mountain lover gift", "cat notebook", "kawaii stationery", "nature coffee mug"]


def main() -> None:
    tracker = PriceTracker()
    for point in SAMPLE_PRICES:
        tracker.record_price(point)
    for signal in SAMPLE_SIGNALS:
        tracker.record_demand_signal(signal)

    analyzer = DemandAnalyzer(tracker)

    # ---- 価格分析 ----
    print("=== 価格分析 ===")
    mug_stats = tracker.get_price_statistics("mug-001")
    competitor_prices = [p.price for p in tracker.get_price_history("mug-001")]
    suggested = tracker.suggest_price_with_competition(SAMPLE_COST, TARGET_MARGIN, competitor_prices)
    print(f"  競合価格 統計: {mug_stats}")
    print(f"  推奨価格 (原価 ${SAMPLE_COST}, マージン {TARGET_MARGIN*100:.0f}%): ${suggested}")

    # ---- 需要分析 ----
    print("\n=== ニッチキーワードランキング ===")
    ranked = analyzer.rank_keywords(KEYWORDS)
    for i, ns in enumerate(ranked, 1):
        mark = "✓ 推奨" if ns.recommended else "  スキップ"
        print(f"  {i}. [{mark}] {ns.keyword}")
        print(f"     需要スコア: {ns.demand_score:.2f}  競合レベル: {ns.competition_level}")

    recommended = analyzer.get_recommended_niches(KEYWORDS)
    print(f"\n推奨ニッチ: {len(recommended)}/{len(KEYWORDS)} 件")

    # ---- JSON 保存 ----
    output = {
        "price_analysis": {
            "product_id": "mug-001",
            "statistics": mug_stats,
            "suggested_price": suggested,
        },
        "keyword_ranking": [
            {
                "keyword": ns.keyword,
                "demand_score": ns.demand_score,
                "competition_level": ns.competition_level,
                "recommended": ns.recommended,
            }
            for ns in ranked
        ],
        "recommended_count": len(recommended),
    }
    output_path = Path("output_analytics.json")
    output_path.write_text(json.dumps(output, ensure_ascii=False, indent=2))
    print(f"\n結果を {output_path} に保存しました。")


if __name__ == "__main__":
    main()
