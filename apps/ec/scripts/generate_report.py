#!/usr/bin/env python3
"""
バッチ結果レポート生成スクリプト。

使い方:
  python scripts/generate_report.py                              # 最新の結果を使用
  python scripts/generate_report.py --input output/results_xxx.json

出力: output/report_YYYYMMDD_HHMMSS.md (Markdown形式)
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path


def find_latest_results(output_dir: Path) -> Path | None:
    """output/ から最新の results_*.json を返す。"""
    candidates = sorted(output_dir.glob("results_*.json"))
    return candidates[-1] if candidates else None


def load_results(input_path: Path) -> list[dict[str, object]]:
    """JSON ファイルを読み込んで結果リストを返す。"""
    text = input_path.read_text(encoding="utf-8")
    data = json.loads(text)
    if not isinstance(data, list):
        raise ValueError(f"結果ファイルはリスト形式である必要があります: {input_path}")
    return data  # type: ignore[return-value]


def classify_result(result: dict[str, object]) -> str:
    """結果を success / copyright_skip / error に分類する。"""
    status = result.get("status", "")
    if status == "success":
        return "success"
    copyright_info = result.get("copyright", {})
    if isinstance(copyright_info, dict):
        risk = copyright_info.get("risk_level", "")
        is_safe = copyright_info.get("is_safe", True)
        if not is_safe or risk in ("high", "medium"):
            return "copyright_skip"
    return "error"


def build_markdown(
    results: list[dict[str, object]],
    input_path: Path,
    generated_at: datetime,
) -> str:
    """結果リストから Markdown レポート文字列を生成する。"""
    total = len(results)

    classified = [(r, classify_result(r)) for r in results]
    success_items = [(r, c) for r, c in classified if c == "success"]
    copyright_items = [(r, c) for r, c in classified if c == "copyright_skip"]
    error_items = [(r, c) for r, c in classified if c == "error"]

    n_success = len(success_items)
    n_copyright = len(copyright_items)
    n_error = len(error_items)

    def pct(n: int) -> str:
        return f"{n / total * 100:.0f}%" if total > 0 else "0%"

    lines: list[str] = []

    # ヘッダー
    lines.append("# 転売自動化 バッチ実行レポート")
    lines.append(f"**実行日時**: {generated_at.strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"**入力ファイル**: {input_path}")
    lines.append("")

    # サマリー
    lines.append("## サマリー")
    lines.append("| 項目 | 件数 | 割合 |")
    lines.append("|------|------|------|")
    lines.append(f"| 処理件数 | {total} | 100% |")
    lines.append(f"| 出品成功 | {n_success} | {pct(n_success)} |")
    lines.append(f"| 著作権スキップ | {n_copyright} | {pct(n_copyright)} |")
    lines.append(f"| エラー | {n_error} | {pct(n_error)} |")
    lines.append("")

    # 成功した出品
    lines.append("## 成功した出品")
    if success_items:
        lines.append("| 商品名 | プラットフォーム | タイトル |")
        lines.append("|--------|----------------|--------|")
        for result, _ in success_items:
            inp = result.get("input", {})
            listing = result.get("listing", {})
            if not isinstance(inp, dict):
                inp = {}
            if not isinstance(listing, dict):
                listing = {}
            name = str(inp.get("name", ""))
            platform = str(inp.get("platform", ""))
            title = str(listing.get("title", ""))
            lines.append(f"| {name} | {platform} | {title} |")
    else:
        lines.append("成功した出品はありません。")
    lines.append("")

    # スキップ・エラー詳細
    lines.append("## スキップ・エラー詳細")
    skip_error_items = copyright_items + error_items
    if skip_error_items:
        lines.append("| 商品名 | 理由 | 著作権リスク |")
        lines.append("|--------|------|------------|")
        for result, category in skip_error_items:
            inp = result.get("input", {})
            copyright_info = result.get("copyright", {})
            if not isinstance(inp, dict):
                inp = {}
            if not isinstance(copyright_info, dict):
                copyright_info = {}
            name = str(inp.get("name", ""))
            error_msg = str(result.get("error", ""))
            risk = str(copyright_info.get("risk_level", "-"))
            if category == "copyright_skip":
                reason = "著作権リスク"
            else:
                reason = error_msg if error_msg else "不明なエラー"
            lines.append(f"| {name} | {reason} | {risk} |")
    else:
        lines.append("スキップ・エラーはありません。")
    lines.append("")

    # 次のアクション
    lines.append("## 次のアクション")
    if n_copyright > 0:
        lines.append(f"- [ ] 著作権スキップ商品のデザイン修正 ({n_copyright}件)")
    if n_success > 0:
        lines.append(f"- [ ] 成功商品の価格設定確認 ({n_success}件)")
    lines.append("- [ ] 出品後24時間後にインプレッション確認")
    if n_error > 0:
        lines.append(f"- [ ] エラー商品の原因調査・再実行 ({n_error}件)")
    lines.append("")

    return "\n".join(lines)


def print_summary(
    results: list[dict[str, object]],
    report_path: Path,
    generated_at: datetime,
) -> None:
    """ターミナルに要約を表示する。"""
    total = len(results)
    n_success = sum(1 for r in results if classify_result(r) == "success")
    n_copyright = sum(1 for r in results if classify_result(r) == "copyright_skip")
    n_error = sum(1 for r in results if classify_result(r) == "error")

    print(f"\n{'=' * 50}")
    print("転売自動化 バッチ実行レポート")
    print(f"実行日時: {generated_at.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'=' * 50}")
    print(f"処理件数:       {total:4d} 件")
    print(f"出品成功:       {n_success:4d} 件")
    print(f"著作権スキップ: {n_copyright:4d} 件")
    print(f"エラー:         {n_error:4d} 件")
    print(f"{'=' * 50}")
    print(f"レポート保存先: {report_path}")


def main() -> None:
    """エントリポイント。"""
    parser = argparse.ArgumentParser(description="バッチ結果レポート生成")
    parser.add_argument(
        "--input",
        type=Path,
        default=None,
        help="入力 JSON ファイルパス（省略時は output/ の最新ファイルを使用）",
    )
    args = parser.parse_args()

    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)

    # 入力ファイルの決定
    input_path: Path | None = args.input
    if input_path is None:
        input_path = find_latest_results(output_dir)
        if input_path is None:
            print("エラー: output/ に results_*.json が見つかりません。")
            print("  --input でファイルを指定するか、先にパイプラインを実行してください。")
            sys.exit(1)
        print(f"最新の結果ファイルを使用: {input_path}")
    else:
        if not input_path.exists():
            print(f"エラー: 指定されたファイルが存在しません: {input_path}")
            sys.exit(1)

    # JSON 読み込み
    try:
        results = load_results(input_path)
    except (json.JSONDecodeError, ValueError) as exc:
        print(f"エラー: JSON の読み込みに失敗しました: {exc}")
        sys.exit(1)

    generated_at = datetime.now()

    # Markdown 生成
    markdown = build_markdown(results, input_path, generated_at)

    # 保存
    report_filename = f"report_{generated_at.strftime('%Y%m%d_%H%M%S')}.md"
    report_path = output_dir / report_filename
    report_path.write_text(markdown, encoding="utf-8")

    # ターミナル要約
    print_summary(results, report_path, generated_at)


if __name__ == "__main__":
    main()
