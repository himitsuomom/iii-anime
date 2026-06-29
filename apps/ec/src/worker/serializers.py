"""iii ワーカー境界の (de)serialization。

エンジンとは JSON (dict) でやり取りするため、EC のドメイン dataclass と
プレーンな dict を相互変換する純粋関数をここに集約する。ネットワーク・エンジン
非依存なのでオフラインでユニットテストできる。
"""

from typing import Any

from src.analytics.demand_analyzer import NicheScore
from src.pipeline import PipelineResult
from src.product.copyright_checker import CopyrightCheckResult
from src.product.models import Language, Platform, ProductInput, ProductListing


def _as_str_list(value: Any) -> list[str]:
    """任意の入力を文字列リストへ正規化する（None/非リストも安全に扱う）。"""
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    return [str(v) for v in value]


def product_input_from_dict(data: dict[str, Any]) -> ProductInput:
    """trigger payload (dict) を ProductInput に変換する。

    必須項目が欠けている場合は ValueError を送出し、エンジン側にエラーを返す。
    platform / language は未知値を既定値にフォールバックする。
    """
    missing = [k for k in ("name", "category", "design_concept", "target_audience") if not data.get(k)]
    if missing:
        raise ValueError(f"必須フィールドが不足しています: {', '.join(missing)}")

    platform_raw = str(data.get("platform", Platform.SHOPIFY.value))
    language_raw = str(data.get("language", Language.EN.value))
    try:
        platform = Platform(platform_raw)
    except ValueError:
        platform = Platform.SHOPIFY
    try:
        language = Language(language_raw)
    except ValueError:
        language = Language.EN

    return ProductInput(
        name=str(data["name"]),
        category=str(data["category"]),
        design_concept=str(data["design_concept"]),
        target_audience=str(data["target_audience"]),
        platform=platform,
        language=language,
        price_range=str(data.get("price_range", "")),
        niche_keywords=_as_str_list(data.get("niche_keywords")),
    )


def product_input_to_dict(inp: ProductInput) -> dict[str, Any]:
    """ProductInput を JSON 互換 dict に変換する。"""
    return {
        "name": inp.name,
        "category": inp.category,
        "design_concept": inp.design_concept,
        "target_audience": inp.target_audience,
        "platform": inp.platform.value,
        "language": inp.language.value,
        "price_range": inp.price_range,
        "niche_keywords": list(inp.niche_keywords),
    }


def product_listing_from_dict(data: dict[str, Any]) -> ProductListing:
    """dict を ProductListing に変換する（listing::* 出品関数の入力用）。

    title/description は必須。platform/language は未知値を既定値にフォールバック。
    """
    title = str(data.get("title", "")).strip()
    description = str(data.get("description", "")).strip()
    if not title or not description:
        raise ValueError("title と description は必須です。")

    platform_raw = str(data.get("platform", Platform.SHOPIFY.value))
    language_raw = str(data.get("language", Language.EN.value))
    try:
        platform = Platform(platform_raw)
    except ValueError:
        platform = Platform.SHOPIFY
    try:
        language = Language(language_raw)
    except ValueError:
        language = Language.EN

    return ProductListing(
        title=title,
        description=description,
        bullet_points=_as_str_list(data.get("bullet_points")),
        tags=_as_str_list(data.get("tags")),
        seo_keywords=_as_str_list(data.get("seo_keywords")),
        platform=platform,
        language=language,
    )


def product_listing_to_dict(listing: ProductListing) -> dict[str, Any]:
    """ProductListing を JSON 互換 dict に変換する。"""
    return {
        "title": listing.title,
        "description": listing.description,
        "bullet_points": list(listing.bullet_points),
        "tags": list(listing.tags),
        "seo_keywords": list(listing.seo_keywords),
        "platform": listing.platform.value,
        "language": listing.language.value,
    }


def copyright_result_to_dict(result: CopyrightCheckResult) -> dict[str, Any]:
    """CopyrightCheckResult を JSON 互換 dict に変換する。"""
    return {
        "is_safe": result.is_safe,
        "risk_level": result.risk_level,
        "issues": list(result.issues),
        "recommendation": result.recommendation,
    }


def niche_score_to_dict(score: NicheScore) -> dict[str, Any]:
    """NicheScore を JSON 互換 dict に変換する。"""
    return {
        "keyword": score.keyword,
        "demand_score": score.demand_score,
        "competition_level": score.competition_level,
        "recommended": score.recommended,
    }


def pipeline_result_to_dict(result: PipelineResult) -> dict[str, Any]:
    """PipelineResult を JSON 互換 dict に変換する。"""
    return {
        "success": result.success,
        "error": result.error,
        "product_input": product_input_to_dict(result.product_input),
        "copyright_result": copyright_result_to_dict(result.copyright_result),
        "listing": (product_listing_to_dict(result.listing) if result.listing is not None else None),
        "shopify_response": result.shopify_response,
    }
