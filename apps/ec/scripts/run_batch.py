#!/usr/bin/env python3
"""
バッチ自動化スクリプト。

使い方:
  python scripts/run_batch.py                          # data/sample_products.csv を使用
  python scripts/run_batch.py --input my_products.csv  # カスタム CSV
  python scripts/run_batch.py --input products.json    # JSON も対応
  python scripts/run_batch.py --dry-run                # APIを叩かずバリデーションのみ

環境変数（.env）:
  ANTHROPIC_API_KEY  -- 必須
  SHOPIFY_STORE_URL, SHOPIFY_ACCESS_TOKEN  -- Shopify出品時に必要（省略可）

出力:
  output/results_YYYYMMDD_HHMMSS.csv  -- 結果CSV（毎回タイムスタンプ付き）
  output/results_YYYYMMDD_HHMMSS.json -- 結果JSON
"""

import argparse
import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

from src.io.product_loader import (  # noqa: E402
    load_from_csv,
    load_from_json,
    save_results_to_csv,
    save_results_to_json,
)
from src.pipeline import PipelineResult, ResalePipeline  # noqa: E402
from src.product.copyright_checker import CopyrightChecker  # noqa: E402
from src.product.generator import ProductGenerator  # noqa: E402
from src.product.models import ProductInput  # noqa: E402


def _result_to_dict(result: PipelineResult) -> dict[str, object]:
    return {
        "name": result.product_input.name,
        "platform": result.product_input.platform.value,
        "success": result.success,
        "title": result.listing.title if result.listing else "",
        "description": result.listing.description if result.listing else "",
        "copyright_safe": result.copyright_result.is_safe,
        "copyright_risk_level": result.copyright_result.risk_level,
        "error": result.error,
    }


def _load_inputs(input_path: Path) -> list[ProductInput]:
    """ファイル拡張子に応じて CSV か JSON を読み込む。"""
    suffix = input_path.suffix.lower()
    if suffix == ".json":
        return load_from_json(input_path)
    return load_from_csv(input_path)


def _print_summary(
    records: list[dict[str, object]],
    csv_path: Path,
    json_path: Path,
) -> None:
    total = len(records)
    success_count = sum(1 for r in records if r.get("success"))
    skipped_count = sum(
        1 for r in records if not r.get("success") and not r.get("copyright_safe")
    )
    error_count = sum(
        1 for r in records if not r.get("success") and r.get("copyright_safe")
    )
    success_pct = int(success_count / total * 100) if total else 0

    print("=" * 60)
    print(" バッチ処理完了")
    print("=" * 60)
    print(f" 処理件数:   {total}")
    print(f" 成功:       {success_count}  ({success_pct}%)")
    print(f" スキップ:   {skipped_count}  (著作権リスク)")
    print(f" エラー:     {error_count}")
    print()
    print("保存先:")
    print(f" {csv_path}")
    print(f" {json_path}")
    print("=" * 60)


async def _run_batch(inputs: list[ProductInput]) -> list[PipelineResult]:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    generator = ProductGenerator(api_key=api_key)
    checker = CopyrightChecker(api_key=api_key)
    pipeline = ResalePipeline(generator=generator, checker=checker)
    return await pipeline.run_batch(inputs)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="商品CSVを読み込み、著作権チェック→説明文生成→出品を一括実行する。"
    )
    parser.add_argument(
        "--input",
        "-i",
        default="data/sample_products.csv",
        help="入力ファイルのパス（CSV または JSON）。デフォルト: data/sample_products.csv",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="APIを呼ばずに入力バリデーションのみ実行する。",
    )
    args = parser.parse_args()

    project_root = Path(__file__).parent.parent
    input_path = Path(args.input)
    if not input_path.is_absolute():
        input_path = project_root / input_path

    # 入力ファイルを読み込む
    print(f"入力ファイル: {input_path}")
    try:
        inputs = _load_inputs(input_path)
    except FileNotFoundError as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"[ERROR] 入力データエラー: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"読み込み完了: {len(inputs)} 件")

    if args.dry_run:
        print("\n[DRY RUN] バリデーション完了。API は呼び出しませんでした。")
        for inp in inputs:
            print(f"  - {inp.name} ({inp.platform.value}/{inp.language.value})")
        return

    # ANTHROPIC_API_KEY の確認
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        print(
            "[ERROR] ANTHROPIC_API_KEY が設定されていません。.env ファイルを確認してください。",
            file=sys.stderr,
        )
        sys.exit(1)

    # output/ ディレクトリを自動作成
    output_dir = project_root / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    # バッチ実行
    print("\nバッチ処理を開始します...")
    results = asyncio.run(_run_batch(inputs))

    # 結果をタイムスタンプ付きファイルに保存
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = output_dir / f"results_{timestamp}.csv"
    json_path = output_dir / f"results_{timestamp}.json"

    records = [_result_to_dict(r) for r in results]
    save_results_to_csv(records, csv_path)
    save_results_to_json(records, json_path)

    _print_summary(records, csv_path, json_path)


if __name__ == "__main__":
    main()
