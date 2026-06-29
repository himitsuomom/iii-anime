"""src/io/product_loader.py のテスト。"""

import csv
import json
from pathlib import Path

import pytest

from src.io.product_loader import (
    load_from_csv,
    load_from_json,
    save_results_to_csv,
    save_results_to_json,
)
from src.product.models import Language, Platform, ProductInput

# ---------------------------------------------------------------------------
# ヘルパー
# ---------------------------------------------------------------------------


def _write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str] | None = None) -> None:
    if fieldnames is None:
        fieldnames = list(rows[0].keys()) if rows else []
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _write_json(path: Path, data: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# load_from_csv
# ---------------------------------------------------------------------------


class TestLoadFromCsv:
    def test_load_all_fields(self, tmp_path: Path) -> None:
        """全フィールドが正しく読み込まれること。"""
        csv_path = tmp_path / "products.csv"
        _write_csv(
            csv_path,
            [
                {
                    "name": "Test Mug",
                    "category": "Home & Kitchen",
                    "design_concept": "Simple design",
                    "target_audience": "Everyone",
                    "platform": "shopify",
                    "language": "en",
                    "price_range": "$18-25",
                    "niche_keywords": "mug|gift|home",
                }
            ],
        )
        results = load_from_csv(csv_path)

        assert len(results) == 1
        p = results[0]
        assert isinstance(p, ProductInput)
        assert p.name == "Test Mug"
        assert p.category == "Home & Kitchen"
        assert p.design_concept == "Simple design"
        assert p.target_audience == "Everyone"
        assert p.platform == Platform.SHOPIFY
        assert p.language == Language.EN
        assert p.price_range == "$18-25"
        assert p.niche_keywords == ["mug", "gift", "home"]

    def test_load_required_fields_only(self, tmp_path: Path) -> None:
        """必須フィールドのみのCSVでデフォルト値が使われること。"""
        csv_path = tmp_path / "minimal.csv"
        _write_csv(
            csv_path,
            [
                {
                    "name": "Minimal Product",
                    "category": "Art",
                    "design_concept": "Abstract",
                    "target_audience": "Adults",
                }
            ],
            fieldnames=["name", "category", "design_concept", "target_audience"],
        )
        results = load_from_csv(csv_path)

        assert len(results) == 1
        p = results[0]
        assert p.platform == Platform.SHOPIFY  # デフォルト
        assert p.language == Language.EN  # デフォルト
        assert p.price_range == ""
        assert p.niche_keywords == []

    def test_load_multiple_rows(self, tmp_path: Path) -> None:
        """複数行が全て読み込まれること。"""
        csv_path = tmp_path / "multi.csv"
        _write_csv(
            csv_path,
            [
                {
                    "name": "Product A",
                    "category": "Cat A",
                    "design_concept": "D A",
                    "target_audience": "T A",
                    "platform": "etsy",
                    "language": "en",
                    "price_range": "",
                    "niche_keywords": "",
                },
                {
                    "name": "Product B",
                    "category": "Cat B",
                    "design_concept": "D B",
                    "target_audience": "T B",
                    "platform": "amazon",
                    "language": "ja",
                    "price_range": "$10",
                    "niche_keywords": "keyword1|keyword2",
                },
            ],
        )
        results = load_from_csv(csv_path)

        assert len(results) == 2
        assert results[0].platform == Platform.ETSY
        assert results[1].platform == Platform.AMAZON
        assert results[1].language == Language.JA
        assert results[1].niche_keywords == ["keyword1", "keyword2"]

    def test_load_all_platforms(self, tmp_path: Path) -> None:
        """全プラットフォーム値が正しく変換されること。"""
        platforms = ["shopify", "etsy", "amazon", "mercari"]
        rows = [
            {
                "name": f"Prod {p}",
                "category": "C",
                "design_concept": "D",
                "target_audience": "T",
                "platform": p,
                "language": "en",
                "price_range": "",
                "niche_keywords": "",
            }
            for p in platforms
        ]
        csv_path = tmp_path / "platforms.csv"
        _write_csv(csv_path, rows)
        results = load_from_csv(csv_path)

        assert [r.platform.value for r in results] == platforms

    def test_invalid_platform_raises_value_error(self, tmp_path: Path) -> None:
        """不正な platform 値で ValueError が発生すること。"""
        csv_path = tmp_path / "bad_platform.csv"
        _write_csv(
            csv_path,
            [
                {
                    "name": "Bad",
                    "category": "C",
                    "design_concept": "D",
                    "target_audience": "T",
                    "platform": "invalid_platform",
                    "language": "en",
                    "price_range": "",
                    "niche_keywords": "",
                }
            ],
        )
        with pytest.raises(ValueError, match="platform"):
            load_from_csv(csv_path)

    def test_invalid_language_raises_value_error(self, tmp_path: Path) -> None:
        """不正な language 値で ValueError が発生すること。"""
        csv_path = tmp_path / "bad_lang.csv"
        _write_csv(
            csv_path,
            [
                {
                    "name": "Bad",
                    "category": "C",
                    "design_concept": "D",
                    "target_audience": "T",
                    "platform": "shopify",
                    "language": "fr",
                    "price_range": "",
                    "niche_keywords": "",
                }
            ],
        )
        with pytest.raises(ValueError, match="language"):
            load_from_csv(csv_path)

    def test_file_not_found_raises_error(self) -> None:
        """存在しないファイルで FileNotFoundError が発生すること。"""
        with pytest.raises(FileNotFoundError):
            load_from_csv("/nonexistent/path/products.csv")

    def test_niche_keywords_pipe_split(self, tmp_path: Path) -> None:
        """niche_keywords が | で正しく分割されること。"""
        csv_path = tmp_path / "keywords.csv"
        _write_csv(
            csv_path,
            [
                {
                    "name": "KW Test",
                    "category": "C",
                    "design_concept": "D",
                    "target_audience": "T",
                    "platform": "shopify",
                    "language": "en",
                    "price_range": "",
                    "niche_keywords": "kw1|kw2|kw3",
                }
            ],
        )
        results = load_from_csv(csv_path)
        assert results[0].niche_keywords == ["kw1", "kw2", "kw3"]

    def test_empty_niche_keywords(self, tmp_path: Path) -> None:
        """niche_keywords が空のとき空リストになること。"""
        csv_path = tmp_path / "empty_kw.csv"
        _write_csv(
            csv_path,
            [
                {
                    "name": "No KW",
                    "category": "C",
                    "design_concept": "D",
                    "target_audience": "T",
                    "platform": "shopify",
                    "language": "en",
                    "price_range": "",
                    "niche_keywords": "",
                }
            ],
        )
        results = load_from_csv(csv_path)
        assert results[0].niche_keywords == []


# ---------------------------------------------------------------------------
# load_from_json
# ---------------------------------------------------------------------------


class TestLoadFromJson:
    def test_load_basic_json(self, tmp_path: Path) -> None:
        """JSONファイルから ProductInput が正しく読み込まれること。"""
        json_path = tmp_path / "products.json"
        _write_json(
            json_path,
            [
                {
                    "name": "JSON Product",
                    "category": "Art",
                    "design_concept": "Colorful abstract",
                    "target_audience": "Art lovers",
                    "platform": "etsy",
                    "language": "en",
                    "price_range": "$20-30",
                    "niche_keywords": ["art", "abstract", "colorful"],
                }
            ],
        )
        results = load_from_json(json_path)

        assert len(results) == 1
        p = results[0]
        assert p.name == "JSON Product"
        assert p.platform == Platform.ETSY
        assert p.language == Language.EN
        assert p.price_range == "$20-30"
        assert p.niche_keywords == ["art", "abstract", "colorful"]

    def test_load_json_multiple_items(self, tmp_path: Path) -> None:
        """複数アイテムが全て読み込まれること。"""
        json_path = tmp_path / "multi.json"
        _write_json(
            json_path,
            [
                {
                    "name": "Item 1",
                    "category": "C1",
                    "design_concept": "D1",
                    "target_audience": "T1",
                    "platform": "shopify",
                    "language": "en",
                },
                {
                    "name": "Item 2",
                    "category": "C2",
                    "design_concept": "D2",
                    "target_audience": "T2",
                    "platform": "mercari",
                    "language": "ja",
                },
            ],
        )
        results = load_from_json(json_path)

        assert len(results) == 2
        assert results[0].name == "Item 1"
        assert results[1].platform == Platform.MERCARI
        assert results[1].language == Language.JA

    def test_load_json_defaults(self, tmp_path: Path) -> None:
        """省略フィールドがデフォルト値になること。"""
        json_path = tmp_path / "minimal.json"
        _write_json(
            json_path,
            [
                {
                    "name": "Minimal",
                    "category": "C",
                    "design_concept": "D",
                    "target_audience": "T",
                }
            ],
        )
        results = load_from_json(json_path)

        assert results[0].platform == Platform.SHOPIFY
        assert results[0].language == Language.EN
        assert results[0].price_range == ""
        assert results[0].niche_keywords == []

    def test_load_json_invalid_platform(self, tmp_path: Path) -> None:
        """JSON で不正な platform 値のとき ValueError が発生すること。"""
        json_path = tmp_path / "bad.json"
        _write_json(
            json_path,
            [{"name": "X", "category": "C", "design_concept": "D", "target_audience": "T", "platform": "bad"}],
        )
        with pytest.raises(ValueError, match="platform"):
            load_from_json(json_path)

    def test_json_file_not_found(self) -> None:
        """存在しないJSONファイルで FileNotFoundError が発生すること。"""
        with pytest.raises(FileNotFoundError):
            load_from_json("/nonexistent/products.json")


# ---------------------------------------------------------------------------
# save_results_to_csv
# ---------------------------------------------------------------------------


class TestSaveResultsToCsv:
    def test_save_and_reload(self, tmp_path: Path) -> None:
        """保存した CSV が正しく読み込めること。"""
        records: list[dict[str, object]] = [
            {
                "name": "Mug",
                "platform": "shopify",
                "success": True,
                "title": "Cool Mug",
                "description": "A great mug",
                "error": "",
                "copyright_safe": True,
                "copyright_risk_level": "low",
            }
        ]
        csv_path = tmp_path / "results.csv"
        save_results_to_csv(records, csv_path)

        assert csv_path.exists()
        with csv_path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert len(rows) == 1
        assert rows[0]["name"] == "Mug"
        assert rows[0]["title"] == "Cool Mug"

    def test_save_creates_parent_dirs(self, tmp_path: Path) -> None:
        """親ディレクトリが存在しなくても自動作成されること。"""
        csv_path = tmp_path / "nested" / "deep" / "results.csv"
        save_results_to_csv([{"name": "X", "platform": "shopify", "success": True, "title": "", "description": "", "error": "", "copyright_safe": True, "copyright_risk_level": "low"}], csv_path)
        assert csv_path.exists()

    def test_save_multiple_records(self, tmp_path: Path) -> None:
        """複数レコードが全て保存されること。"""
        records: list[dict[str, object]] = [
            {"name": f"Product {i}", "platform": "shopify", "success": True, "title": f"Title {i}", "description": "", "error": "", "copyright_safe": True, "copyright_risk_level": "low"}
            for i in range(5)
        ]
        csv_path = tmp_path / "multi.csv"
        save_results_to_csv(records, csv_path)

        with csv_path.open(newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == 5


# ---------------------------------------------------------------------------
# save_results_to_json
# ---------------------------------------------------------------------------


class TestSaveResultsToJson:
    def test_save_and_reload(self, tmp_path: Path) -> None:
        """保存したJSONが正しく読み込めること。"""
        records: list[dict[str, object]] = [
            {
                "name": "Poster",
                "platform": "etsy",
                "success": False,
                "title": "",
                "description": "",
                "error": "著作権リスク",
                "copyright_safe": False,
                "copyright_risk_level": "high",
            }
        ]
        json_path = tmp_path / "results.json"
        save_results_to_json(records, json_path)

        assert json_path.exists()
        with json_path.open(encoding="utf-8") as f:
            data = json.load(f)

        assert len(data) == 1
        assert data[0]["name"] == "Poster"
        assert data[0]["error"] == "著作権リスク"
        assert data[0]["copyright_safe"] is False

    def test_save_json_unicode(self, tmp_path: Path) -> None:
        """日本語が ensure_ascii=False で保存されること。"""
        records: list[dict[str, object]] = [
            {"name": "日本語商品", "platform": "mercari", "success": True, "title": "タイトル", "description": "説明文", "error": "", "copyright_safe": True, "copyright_risk_level": "low"}
        ]
        json_path = tmp_path / "unicode.json"
        save_results_to_json(records, json_path)

        raw = json_path.read_text(encoding="utf-8")
        assert "日本語商品" in raw  # エスケープされていないこと
        assert "タイトル" in raw

    def test_save_json_creates_parent_dirs(self, tmp_path: Path) -> None:
        """親ディレクトリが存在しなくても自動作成されること。"""
        json_path = tmp_path / "nested" / "results.json"
        save_results_to_json([], json_path)
        assert json_path.exists()

    def test_save_json_indented(self, tmp_path: Path) -> None:
        """indent=2 で保存されること（改行が含まれること）。"""
        records: list[dict[str, object]] = [{"name": "X", "success": True}]
        json_path = tmp_path / "indented.json"
        save_results_to_json(records, json_path)

        raw = json_path.read_text(encoding="utf-8")
        assert "\n" in raw  # インデントで改行が含まれる
