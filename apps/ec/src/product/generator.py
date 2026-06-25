"""Claude APIを使った商品説明文の自動生成。"""

import json
import re

import anthropic

from src.config import (
    ANTHROPIC_API_KEY,
    CLAUDE_MAX_TOKENS,
    CLAUDE_MODEL,
    PLATFORM_LIMITS,
)
from src.product.models import Language, ProductInput, ProductListing

_SYSTEM_PROMPT = """\
あなたはShopify・Amazon・Etsy・メルカリに精通したECコピーライターです。
SEO最適化・高コンバージョン・著作権リスクゼロの商品説明文を生成します。

ルール：
- 商標・キャラクター・著名人・ロゴを想起させる表現を絶対に使わない
- 誇大広告表現（「世界一」「完璧」等）を使わない
- 指定フォーマットのJSONのみを出力する（前後にテキスト不要）\
"""


def _build_user_prompt(inp: ProductInput, limits: dict[str, int]) -> str:
    lang_instruction = (
        "Generate in English." if inp.language == Language.EN else "日本語で生成してください。"
    )
    niche_hint = (
        f"Niche keywords to naturally include: {', '.join(inp.niche_keywords)}"
        if inp.niche_keywords
        else ""
    )
    price_hint = f"Price range: {inp.price_range}" if inp.price_range else ""

    bullet_count = limits.get("bullet_points_max", 5)
    title_max = limits.get("title_max", 255)
    tag_count = limits.get("tags_max_count", 13)
    tag_chars = limits.get("tag_max_chars", 20)

    return f"""
Product information:
- Name: {inp.name}
- Category: {inp.category}
- Design concept: {inp.design_concept}
- Target audience: {inp.target_audience}
{price_hint}
{niche_hint}

Platform: {inp.platform.value}
{lang_instruction}

Output requirements:
- title: under {title_max} characters, SEO-optimized
- description: 150-300 characters, compelling and conversion-focused
- bullet_points: exactly {bullet_count} items, each highlighting a key benefit
- tags: {tag_count} tags, each under {tag_chars} characters, no trademarks
- seo_keywords: 5-8 natural search keywords

Output ONLY valid JSON in this exact format:
{{
  "title": "...",
  "description": "...",
  "bullet_points": ["...", "...", "...", "...", "..."],
  "tags": ["...", "..."],
  "seo_keywords": ["...", "..."]
}}
""".strip()


class ProductGenerator:
    """Claude APIを使った商品説明文ジェネレーター。"""

    def __init__(self, api_key: str = ANTHROPIC_API_KEY) -> None:
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY が未設定です。.env を確認してください。")
        self._client = anthropic.Anthropic(api_key=api_key)

    def generate(self, inp: ProductInput) -> ProductListing:
        """商品情報からリスティングを生成する（同期版）。"""
        limits = PLATFORM_LIMITS.get(inp.platform.value, PLATFORM_LIMITS["shopify"])
        user_prompt = _build_user_prompt(inp, limits)

        response = self._client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=CLAUDE_MAX_TOKENS,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )

        raw = response.content[0].text.strip()
        return self._parse_response(raw, inp)

    def generate_batch(self, inputs: list[ProductInput]) -> list[ProductListing]:
        """複数商品を順番に生成する。レート制限を考慮してsleep不要（同期呼び出しのため）。"""
        return [self.generate(inp) for inp in inputs]

    @staticmethod
    def _parse_response(raw: str, inp: ProductInput) -> ProductListing:
        """JSONレスポンスをProductListingに変換。パース失敗時は詳細なエラーを返す。"""
        # コードブロック除去（```json ... ``` の場合）
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.MULTILINE).strip()
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Claude APIのレスポンスがJSON形式ではありません: {e}\n---\n{raw}"
            ) from e

        return ProductListing(
            title=data.get("title", ""),
            description=data.get("description", ""),
            bullet_points=data.get("bullet_points", []),
            tags=data.get("tags", []),
            seo_keywords=data.get("seo_keywords", []),
            platform=inp.platform,
            language=inp.language,
        )
