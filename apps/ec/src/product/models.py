"""商品データモデル。全フィールドに型注釈必須。"""

from dataclasses import dataclass, field
from enum import StrEnum


class Platform(StrEnum):
    SHOPIFY = "shopify"
    MERCARI = "mercari"
    ETSY = "etsy"
    AMAZON = "amazon"


class Language(StrEnum):
    EN = "en"
    JA = "ja"


@dataclass
class ProductInput:
    """Claude APIへの入力データ。"""

    name: str
    category: str
    design_concept: str
    target_audience: str
    platform: Platform = Platform.SHOPIFY
    language: Language = Language.EN
    price_range: str = ""
    niche_keywords: list[str] = field(default_factory=list)


@dataclass
class ProductListing:
    """生成された商品リスティングデータ。"""

    title: str
    description: str
    bullet_points: list[str]
    tags: list[str]
    seo_keywords: list[str]
    platform: Platform
    language: Language

    def to_shopify_payload(self) -> dict[str, object]:
        """Shopify Product APIのリクエストボディ形式に変換。"""
        return {
            "product": {
                "title": self.title,
                "body_html": f"<p>{self.description}</p>"
                + "".join(f"<li>{bp}</li>" for bp in self.bullet_points),
                "tags": ",".join(self.tags),
                "metafields": [
                    {
                        "namespace": "seo",
                        "key": "hidden",
                        "value": ",".join(self.seo_keywords),
                        "type": "single_line_text_field",
                    }
                ],
            }
        }

    def to_amazon_payload(self) -> dict[str, object]:
        """PODtomatic/Amazon出品形式に変換。"""
        return {
            "title": self.title,
            "description": self.description,
            "bullet_points": self.bullet_points[:5],
            "keywords": " ".join(self.seo_keywords),
        }
