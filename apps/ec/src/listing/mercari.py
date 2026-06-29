"""メルカリ API クライアント。商品を非同期で出品する。"""

import json

import httpx

from src.config import MERCARI_ACCESS_TOKEN
from src.product.models import ProductListing

_TITLE_MAX = 40
_DESC_MAX = 1000


class MercariListing:
    """メルカリ API を使った商品出品クライアント。

    文字数制限: タイトル最大40文字、説明最大1000文字。
    """

    BASE_URL = "https://api.mercari.jp"

    def __init__(self, access_token: str = MERCARI_ACCESS_TOKEN) -> None:
        if not access_token:
            raise ValueError(
                "MERCARI_ACCESS_TOKEN を .env に設定してください。"
            )
        self._headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

    def _validate_listing(self, listing: ProductListing) -> None:
        """タイトル・説明の文字数制限を検証する。"""
        if len(listing.title) > _TITLE_MAX:
            raise ValueError(
                f"メルカリ タイトルは{_TITLE_MAX}文字以内にしてください（現在: {len(listing.title)}文字）"
            )
        if len(listing.description) > _DESC_MAX:
            raise ValueError(
                f"メルカリ 説明文は{_DESC_MAX}文字以内にしてください（現在: {len(listing.description)}文字）"
            )

    def _build_payload(self, listing: ProductListing, price: int) -> dict[str, object]:
        """出品用ペイロードを生成する。"""
        return {
            "name": listing.title,
            "description": listing.description,
            "price": price,
            "category_id": 1,
            "status": "on_sale",
        }

    async def create_product(
        self, listing: ProductListing, price: int = 1000
    ) -> dict[str, object]:
        """商品を1件メルカリに出品する。成功時はレスポンスの dict を返す。"""
        self._validate_listing(listing)
        payload = self._build_payload(listing, price)

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.BASE_URL}/items/add",
                headers=self._headers,
                content=json.dumps(payload),
                timeout=30.0,
            )

        if response.status_code != 200:
            raise RuntimeError(
                f"メルカリ API エラー {response.status_code}: {response.text[:500]}"
            )

        return response.json()  # type: ignore[no-any-return]

    async def create_products_batch(
        self, listings: list[tuple[ProductListing, int]]
    ) -> list[dict[str, object]]:
        """複数商品を順次出品する。listings は (ProductListing, price) のリスト。"""
        results = []
        for listing, price in listings:
            result = await self.create_product(listing, price)
            results.append(result)
        return results
