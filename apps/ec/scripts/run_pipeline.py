#!/usr/bin/env python3
"""POD転売 自動説明文生成スクリプト。
使い方: python scripts/run_pipeline.py
環境変数: ANTHROPIC_API_KEY（必須）
"""

import json
import os
import sys
from pathlib import Path

# プロジェクトルートを sys.path に追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

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


def main() -> None:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("エラー: ANTHROPIC_API_KEY が未設定です。.env を確認してください。")
        sys.exit(1)

    gen = ProductGenerator(api_key=api_key)
    results = []

    for i, inp in enumerate(SAMPLE_PRODUCTS, 1):
        print(f"\n[{i}/{len(SAMPLE_PRODUCTS)}] 生成中: {inp.name} ({inp.platform})")
        try:
            listing = gen.generate(inp)
            result: dict[str, object] = {
                "input": {"name": inp.name, "platform": inp.platform.value},
                "listing": {
                    "title": listing.title,
                    "description": listing.description,
                    "bullet_points": listing.bullet_points,
                    "tags": listing.tags,
                    "seo_keywords": listing.seo_keywords,
                },
                "status": "success",
            }
            print(f"  タイトル: {listing.title}")
        except Exception as e:
            result = {"input": {"name": inp.name}, "status": "error", "error": str(e)}
            print(f"  エラー: {e}")

        results.append(result)

    # 結果をJSONファイルに保存
    output_path = Path("output_listings.json")
    output_path.write_text(json.dumps(results, ensure_ascii=False, indent=2))
    print(f"\n完了！結果を {output_path} に保存しました。")
    print(f"成功: {sum(1 for r in results if r['status'] == 'success')} / {len(results)}")


if __name__ == "__main__":
    main()
