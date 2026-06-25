"""PODtomatic API クライアント。Amazon POD商品を自動アップロードする。"""

import json

import httpx

from src.config import PODTOMATIC_API_KEY, PODTOMATIC_DAILY_UPLOAD_LIMIT
from src.product.models import ProductListing


class PodtomaticListing:
    """PODtomatic API を使った Amazon POD 商品アップロードクライアント。

    1日最大 200 商品のアップロード制限を _check_daily_limit() で管理する。
    """

    BASE_URL = "https://api.podtomatic.com/v1"

    def __init__(self, api_key: str = PODTOMATIC_API_KEY) -> None:
        if not api_key:
            raise ValueError(
                "PODTOMATIC_API_KEY を .env に設定してください。"
            )
        self._api_key = api_key
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        self._daily_upload_count: int = 0

    def _check_daily_limit(self) -> None:
        """1日 200 商品上限チェック。超過時は RuntimeError を送出する。"""
        if self._daily_upload_count >= PODTOMATIC_DAILY_UPLOAD_LIMIT:
            raise RuntimeError(
                f"PODtomatic 1日アップロード上限（{PODTOMATIC_DAILY_UPLOAD_LIMIT}件）に達しました。"
            )

    async def upload_product(self, listing: ProductListing) -> dict[str, object]:
        """商品を1件 PODtomatic にアップロードする。

        - _check_daily_limit() を呼んで上限チェック
        - to_amazon_payload() でペイロード生成
        - POST {BASE_URL}/products
        - 成功（201）: daily_upload_count += 1 → response.json() を返す
        - 失敗: RuntimeError を送出する
        """
        self._check_daily_limit()
        payload = listing.to_amazon_payload()

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.BASE_URL}/products",
                headers=self._headers,
                content=json.dumps(payload),
                timeout=30.0,
            )

        if response.status_code != 201:
            raise RuntimeError(
                f"PODtomatic API エラー {response.status_code}: {response.text[:500]}"
            )

        self._daily_upload_count += 1
        return response.json()  # type: ignore[no-any-return]

    async def upload_products_batch(
        self, listings: list[ProductListing]
    ) -> list[dict[str, object]]:
        """複数商品を順次アップロードする（Shopify と同様、並列不可）。"""
        results = []
        for listing in listings:
            result = await self.upload_product(listing)
            results.append(result)
        return results

    def get_daily_upload_count(self) -> int:
        """本日のアップロード数を返す。"""
        return self._daily_upload_count

    def reset_daily_count(self) -> None:
        """日次リセット（毎日 0 時に呼ぶ想定）。"""
        self._daily_upload_count = 0
