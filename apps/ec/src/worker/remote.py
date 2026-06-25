"""automation-studio の `ai::describe-product`（opus）へ委譲する説明生成器。

エンジン経由で AS の関数を呼び、応答（`{title, description, bullets,
seoKeywords, source}`）を EC の `ProductListing` に写像する。例外/タイムアウト時は
注入された fallback 生成器（ローカル/オフライン）へ自動退避する。`generate()` を
持つので `GeneratorLike` を満たし、`ResalePipeline` / `products::describe` に
そのまま差し込める（説明生成の一本化）。
"""

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from src.product.models import ProductInput, ProductListing

if TYPE_CHECKING:
    from src.worker.services import GeneratorLike

# iii.trigger 互換のシグネチャ（dict リクエスト → 応答）。
TriggerFn = Callable[[dict[str, Any]], Any]

DESCRIBE_FUNCTION_ID = "ai::describe-product"


class RemoteProductGenerator:
    """`ai::describe-product` に委譲し、失敗時は fallback へ退避する生成器。"""

    def __init__(self, trigger: TriggerFn, fallback: "GeneratorLike") -> None:
        self._trigger = trigger
        self._fallback = fallback

    def generate(self, inp: ProductInput) -> ProductListing:
        """remote 生成を試み、失敗（例外/不正応答）時はローカル生成へ退避する。"""
        try:
            response = self._trigger(
                {"function_id": DESCRIBE_FUNCTION_ID, "payload": _to_request(inp)}
            )
            return _to_listing(response, inp)
        except Exception:  # noqa: BLE001 — remote 失敗は必ずローカルへ退避する
            return self._fallback.generate(inp)


def _to_request(inp: ProductInput) -> dict[str, Any]:
    """ProductInput を ai::describe-product のリクエスト形へ写像する。"""
    features = "; ".join(
        part
        for part in (inp.category, inp.design_concept, f"対象: {inp.target_audience}")
        if part
    )
    return {
        "productName": inp.name,
        "features": features,
        "keywords": ", ".join(inp.niche_keywords),
        "tone": "",
    }


def _to_listing(response: Any, inp: ProductInput) -> ProductListing:
    """ai::describe-product の応答を ProductListing へ写像する。

    title/description が欠ける応答は不正としてエラーにし、呼び出し側で fallback させる。
    AS は tags を返さないため、tags は商品の niche_keywords（無ければ seoKeywords）を使う。
    """
    if not isinstance(response, dict):
        raise ValueError(f"ai::describe-product の応答が dict ではありません: {type(response).__name__}")

    title = str(response.get("title", "")).strip()
    description = str(response.get("description", "")).strip()
    if not title or not description:
        raise ValueError("ai::describe-product の応答に title/description がありません。")

    bullets = [str(b) for b in (response.get("bullets") or [])]
    seo_keywords = [str(k) for k in (response.get("seoKeywords") or [])]
    tags = list(inp.niche_keywords) if inp.niche_keywords else list(seo_keywords)

    return ProductListing(
        title=title,
        description=description,
        bullet_points=bullets,
        tags=tags,
        seo_keywords=seo_keywords,
        platform=inp.platform,
        language=inp.language,
    )
