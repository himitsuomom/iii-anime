"""CSV/JSONファイルから ProductInput を一括ロードするユーティリティ。"""

import csv
import json
from pathlib import Path

from src.product.models import Language, Platform, ProductInput


def load_from_csv(filepath: str | Path) -> list[ProductInput]:
    """CSVファイルから ProductInput リストを読み込む。

    CSVの列: name, category, design_concept, target_audience,
             platform (shopify/etsy/amazon/mercari), language (en/ja),
             price_range (任意), niche_keywords ("|" 区切り、任意)

    - 存在しない列はデフォルト値
    - platform/language は StrEnum に変換（不正値は ValueError）
    - niche_keywords は "|" で区切り

    Args:
        filepath: 読み込む CSV ファイルのパス。

    Returns:
        list[ProductInput]: 読み込んだ ProductInput のリスト。

    Raises:
        FileNotFoundError: ファイルが存在しない場合。
        ValueError: platform または language の値が不正な場合。
    """
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"CSV ファイルが見つかりません: {filepath}")

    results: list[ProductInput] = []
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            platform_raw = row.get("platform", "shopify").strip() or "shopify"
            language_raw = row.get("language", "en").strip() or "en"

            try:
                platform = Platform(platform_raw)
            except ValueError as exc:
                raise ValueError(
                    f"platform の値が不正です: '{platform_raw}'. "
                    f"有効な値: {[p.value for p in Platform]}"
                ) from exc

            try:
                language = Language(language_raw)
            except ValueError as exc:
                raise ValueError(
                    f"language の値が不正です: '{language_raw}'. "
                    f"有効な値: {[la.value for la in Language]}"
                ) from exc

            niche_raw = row.get("niche_keywords", "").strip()
            niche_keywords = [kw.strip() for kw in niche_raw.split("|") if kw.strip()] if niche_raw else []

            results.append(
                ProductInput(
                    name=row.get("name", "").strip(),
                    category=row.get("category", "").strip(),
                    design_concept=row.get("design_concept", "").strip(),
                    target_audience=row.get("target_audience", "").strip(),
                    platform=platform,
                    language=language,
                    price_range=row.get("price_range", "").strip(),
                    niche_keywords=niche_keywords,
                )
            )

    return results


def load_from_json(filepath: str | Path) -> list[ProductInput]:
    """JSONファイルから ProductInput リストを読み込む。

    JSON は ProductInput フィールドのリスト形式。

    Args:
        filepath: 読み込む JSON ファイルのパス。

    Returns:
        list[ProductInput]: 読み込んだ ProductInput のリスト。

    Raises:
        FileNotFoundError: ファイルが存在しない場合。
        ValueError: platform または language の値が不正な場合。
    """
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"JSON ファイルが見つかりません: {filepath}")

    with path.open(encoding="utf-8") as f:
        data = json.load(f)

    results: list[ProductInput] = []
    for item in data:
        platform_raw = item.get("platform", "shopify")
        language_raw = item.get("language", "en")

        try:
            platform = Platform(platform_raw)
        except ValueError as exc:
            raise ValueError(
                f"platform の値が不正です: '{platform_raw}'. "
                f"有効な値: {[p.value for p in Platform]}"
            ) from exc

        try:
            language = Language(language_raw)
        except ValueError as exc:
            raise ValueError(
                f"language の値が不正です: '{language_raw}'. "
                f"有効な値: {[la.value for la in Language]}"
            ) from exc

        niche_keywords = item.get("niche_keywords", [])
        if isinstance(niche_keywords, str):
            niche_keywords = [kw.strip() for kw in niche_keywords.split("|") if kw.strip()]

        results.append(
            ProductInput(
                name=item.get("name", ""),
                category=item.get("category", ""),
                design_concept=item.get("design_concept", ""),
                target_audience=item.get("target_audience", ""),
                platform=platform,
                language=language,
                price_range=item.get("price_range", ""),
                niche_keywords=niche_keywords,
            )
        )

    return results


def save_results_to_csv(results: list[dict[str, object]], filepath: str | Path) -> None:
    """バッチ結果を CSV に保存する。

    各行: name, platform, success, title, description, error, copyright_risk

    Args:
        results: バッチ処理結果の辞書リスト。
        filepath: 保存先 CSV ファイルのパス。
    """
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "name",
        "platform",
        "success",
        "title",
        "description",
        "error",
        "copyright_safe",
        "copyright_risk_level",
    ]

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in results:
            writer.writerow(row)


def save_results_to_json(results: list[dict[str, object]], filepath: str | Path) -> None:
    """バッチ結果を JSON に保存する（ensure_ascii=False, indent=2）。

    Args:
        results: バッチ処理結果の辞書リスト。
        filepath: 保存先 JSON ファイルのパス。
    """
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
