#!/usr/bin/env python3
"""フルパイプライン実行スクリプト。著作権チェック + 説明文生成。
使い方: python scripts/run_full_pipeline.py
環境変数: ANTHROPIC_API_KEY（必須）
"""

import asyncio
import json
import os
import sys
from pathlib import Path

# プロジェクトルートを sys.path に追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

from src.pipeline import ResalePipeline  # noqa: E402
from src.product.copyright_checker import CopyrightChecker  # noqa: E402
from src.product.generator import ProductGenerator  # noqa: E402
from src.product.models import Language, Platform, ProductInput  # noqa: E402

# サンプル商品（実運用では CSV/JSONファイルから読み込む）
SAMPLE_PRODUCTS = [
    ProductInput(
        name="Mountain Sunrise Coffee Mug",
        category="Home & Kitchen / Mugs",
        design_concept="Minimalist mountain silhouette at sunrise, warm orange gradient",
        target_audience="Outdoor enthusiasts, hikers aged 25-45",
        platform=Platform.SHOPIFY,
        language=Language.EN,
        niche_keywords=["hiking mug", "mountain lover gift", "nature coffee mug"],
    ),
    ProductInput(
        name="Cat Lover Notebook",
        category="Office / Notebooks",
        design_concept="Cute cat silhouette with watercolor floral border",
        target_audience="Cat owners, stationery lovers aged 18-35",
        platform=Platform.ETSY,
        language=Language.EN,
        niche_keywords=["cat notebook", "cat lover gift", "kawaii stationery"],
    ),
]


async def run() -> None:
    """フルパイプラインを実行する。"""
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("エラー: ANTHROPIC_API_KEY が未設定です。.env を確認してください。")
        sys.exit(1)

    gen = ProductGenerator(api_key=api_key)
    checker = CopyrightChecker(api_key=api_key)
    # shopify_client=None: 説明文生成まで実行、実際の出品はしない
    pipeline = ResalePipeline(generator=gen, checker=checker)

    print(f"フルパイプライン開始: {len(SAMPLE_PRODUCTS)} 件")
    pipeline_results = await pipeline.run_batch(SAMPLE_PRODUCTS)

    results = []
    for i, (inp, pr) in enumerate(zip(SAMPLE_PRODUCTS, pipeline_results, strict=True), 1):
        print(f"\n[{i}/{len(SAMPLE_PRODUCTS)}] {inp.name} ({inp.platform})")
        if pr.success and pr.listing is not None:
            result: dict[str, object] = {
                "input": {"name": inp.name, "platform": inp.platform.value},
                "copyright": {
                    "is_safe": pr.copyright_result.is_safe,
                    "risk_level": pr.copyright_result.risk_level,
                },
                "listing": {
                    "title": pr.listing.title,
                    "description": pr.listing.description,
                    "bullet_points": pr.listing.bullet_points,
                    "tags": pr.listing.tags,
                    "seo_keywords": pr.listing.seo_keywords,
                },
                "status": "success",
            }
            print(f"  著作権: {pr.copyright_result.risk_level} リスク")
            print(f"  タイトル: {pr.listing.title}")
        else:
            result = {
                "input": {"name": inp.name, "platform": inp.platform.value},
                "copyright": {
                    "is_safe": pr.copyright_result.is_safe,
                    "risk_level": pr.copyright_result.risk_level,
                },
                "status": "error",
                "error": pr.error,
            }
            print(f"  スキップ: {pr.error}")

        results.append(result)

    # 結果をJSONファイルに保存
    output_path = Path("output_full_pipeline.json")
    output_path.write_text(json.dumps(results, ensure_ascii=False, indent=2))
    print(f"\n完了！結果を {output_path} に保存しました。")

    safe_count = sum(1 for r in results if r.get("status") == "success")
    unsafe_count = len(results) - safe_count
    print(f"safe: {safe_count} 件 / unsafe: {unsafe_count} 件 / 合計: {len(results)} 件")


def main() -> None:
    """エントリポイント。"""
    asyncio.run(run())


if __name__ == "__main__":
    main()
