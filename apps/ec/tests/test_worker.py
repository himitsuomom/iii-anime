"""iii ワーカーアダプタ（Phase 2）のテスト。

全テストはオフライン・エンジン非依存（force_offline=True / 偽エンジン）で完結する。
APIキー・ネットワーク・iii SDK は不要。
"""

from typing import Any

import pytest

from src.product.models import Language, Platform, ProductInput
from src.worker.app import register_ec_functions
from src.worker.handlers import (
    handle_analytics_demand,
    handle_analytics_price,
    handle_copyright_check,
    handle_describe,
    handle_pipeline_run,
)
from src.worker.offline import OfflineCopyrightChecker, OfflineProductGenerator
from src.worker.serializers import (
    product_input_from_dict,
    product_input_to_dict,
)
from src.worker.services import Services, build_services


@pytest.fixture
def services() -> Services:
    return build_services(force_offline=True)


@pytest.fixture
def describe_payload() -> dict[str, Any]:
    return {
        "name": "Mountain Sunrise Mug",
        "category": "Home & Kitchen / Mugs",
        "design_concept": "Minimalist mountain silhouette at sunrise",
        "target_audience": "Outdoor enthusiasts aged 25-45",
        "platform": "shopify",
        "language": "en",
        "niche_keywords": ["hiking", "mountain"],
    }


# ---- serializers ----


def test_product_input_roundtrip(describe_payload: dict[str, Any]) -> None:
    inp = product_input_from_dict(describe_payload)
    assert inp.name == "Mountain Sunrise Mug"
    assert inp.platform == Platform.SHOPIFY
    assert inp.language == Language.EN
    assert inp.niche_keywords == ["hiking", "mountain"]
    # to_dict は元の項目を保持する
    out = product_input_to_dict(inp)
    assert out["name"] == describe_payload["name"]
    assert out["platform"] == "shopify"


def test_product_input_missing_field_raises() -> None:
    with pytest.raises(ValueError, match="必須フィールド"):
        product_input_from_dict({"name": "x"})


def test_product_input_unknown_enum_falls_back() -> None:
    inp = product_input_from_dict(
        {
            "name": "n",
            "category": "c",
            "design_concept": "d",
            "target_audience": "t",
            "platform": "nonexistent",
            "language": "xx",
        }
    )
    assert inp.platform == Platform.SHOPIFY
    assert inp.language == Language.EN


# ---- offline 実装 ----


def test_offline_generator_respects_mercari_limits() -> None:
    gen = OfflineProductGenerator()
    inp = ProductInput(
        name="A very long product name that clearly exceeds forty chars limit",
        category="Apparel",
        design_concept="simple stripes",
        target_audience="everyone",
        platform=Platform.MERCARI,
        language=Language.JA,
    )
    listing = gen.generate(inp)
    assert len(listing.title) <= 40
    # メルカリはタグ非対応（上限0）→ 空
    assert listing.tags == []


def test_offline_copyright_flags_risky_terms() -> None:
    checker = OfflineCopyrightChecker()
    result = checker.check(design_description="cute Pokemon inspired art", product_name="mug")
    assert result.is_safe is False
    assert result.risk_level == "high"


def test_offline_copyright_passes_clean_design() -> None:
    checker = OfflineCopyrightChecker()
    result = checker.check(design_description="abstract geometric shapes", product_name="poster")
    assert result.is_safe is True
    assert result.risk_level == "low"


# ---- handlers ----


def test_handle_describe(services: Services, describe_payload: dict[str, Any]) -> None:
    out = handle_describe(describe_payload, services)
    assert out["title"]
    assert isinstance(out["bullet_points"], list)
    assert out["platform"] == "shopify"


def test_handle_copyright_check_accepts_both_key_names(services: Services) -> None:
    out = handle_copyright_check(
        {"name": "poster", "design_description": "plain dots"}, services
    )
    assert out["is_safe"] is True
    out2 = handle_copyright_check(
        {"product_name": "poster", "design_concept": "Disney castle"}, services
    )
    assert out2["is_safe"] is False


def test_handle_copyright_check_requires_fields(services: Services) -> None:
    with pytest.raises(ValueError):
        handle_copyright_check({"name": "x"}, services)


def test_handle_analytics_price(services: Services) -> None:
    out = handle_analytics_price(
        {"cost": 10.0, "target_margin": 0.5, "competitor_prices": [18.0, 25.0]}, services
    )
    # margin price = 20.0, competitor median = 21.5 → min = 20.0
    assert out["suggested_price"] == 20.0
    assert out["competitor_count"] == 2


def test_handle_analytics_price_requires_cost(services: Services) -> None:
    with pytest.raises(ValueError):
        handle_analytics_price({}, services)


def test_handle_analytics_demand_ranks_with_inline_signals(services: Services) -> None:
    out = handle_analytics_demand(
        {
            "keywords": ["minimalist", "vintage"],
            "signals": [
                {"keyword": "minimalist", "search_volume_estimate": 500, "trend_score": 0.9, "platform": "etsy"},
                {"keyword": "vintage", "search_volume_estimate": 50000, "trend_score": 0.4, "platform": "etsy"},
            ],
        },
        services,
    )
    scores = out["scores"]
    assert [s["keyword"] for s in scores] == ["minimalist", "vintage"]
    # minimalist: demand 0.9, low competition → recommended
    assert scores[0]["recommended"] is True
    # vintage: high search volume → high competition → not recommended
    assert scores[1]["recommended"] is False
    assert len(out["recommended"]) == 1


def test_handle_analytics_demand_requires_keywords(services: Services) -> None:
    with pytest.raises(ValueError):
        handle_analytics_demand({}, services)


@pytest.mark.asyncio
async def test_handle_pipeline_run_offline_success(
    services: Services, describe_payload: dict[str, Any]
) -> None:
    out = await handle_pipeline_run(describe_payload, services)
    assert out["success"] is True
    assert out["copyright_result"]["is_safe"] is True
    assert out["listing"] is not None
    # オフライン構成では出品クライアント無し
    assert out["shopify_response"] is None


@pytest.mark.asyncio
async def test_handle_pipeline_run_blocks_risky_design(services: Services) -> None:
    out = await handle_pipeline_run(
        {
            "name": "Hero Tee",
            "category": "Apparel",
            "design_concept": "Marvel superhero logo",
            "target_audience": "fans",
        },
        services,
    )
    assert out["success"] is False
    assert out["listing"] is None
    assert out["copyright_result"]["is_safe"] is False


# ---- registration wiring (fake engine) ----


class _FakeEngine:
    """register_function / register_trigger を記録するだけの偽エンジン。"""

    def __init__(self) -> None:
        self.functions: dict[str, Any] = {}
        self.triggers: list[dict[str, Any]] = []

    def register_function(self, function_id: str, handler: Any) -> None:
        self.functions[function_id] = handler

    def register_trigger(self, trigger: dict[str, Any]) -> None:
        self.triggers.append(trigger)


def test_register_ec_functions_registers_all(services: Services) -> None:
    engine = _FakeEngine()
    register_ec_functions(engine, services)
    assert set(engine.functions) == {
        "products::describe",
        "copyright::check",
        "analytics::price",
        "analytics::demand",
        "pipeline::run",
    }
    # 各関数に HTTP トリガーが1つずつ
    assert len(engine.triggers) == 5
    paths = {t["config"]["api_path"] for t in engine.triggers}
    assert "/ec/describe" in paths
    assert all(t["config"]["http_method"] == "POST" for t in engine.triggers)


def test_registered_sync_handler_unwraps_http_request(
    services: Services, describe_payload: dict[str, Any]
) -> None:
    engine = _FakeEngine()
    register_ec_functions(engine, services)
    describe = engine.functions["products::describe"]
    # 直接 payload
    direct = describe(describe_payload)
    # ApiRequest 形（body にネスト）
    wrapped = describe({"method": "POST", "headers": {}, "body": describe_payload})
    assert direct == wrapped
    assert direct["title"]


def test_registered_handlers_are_distinct_closures(services: Services) -> None:
    # ループ内クロージャのバインド漏れ（全部最後のハンドラを指す）を防ぐ回帰テスト
    engine = _FakeEngine()
    register_ec_functions(engine, services)
    price = engine.functions["analytics::price"]({"cost": 10.0})
    copyright_out = engine.functions["copyright::check"](
        {"name": "p", "design_concept": "plain"}
    )
    assert "suggested_price" in price
    assert "is_safe" in copyright_out
