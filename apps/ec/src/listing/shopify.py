"""Shopify Product API クライアント。レート制限を守って非同期で出品する。"""

import asyncio
import json
import time

import httpx

from src.config import (
    SHOPIFY_ACCESS_TOKEN,
    SHOPIFY_API_VERSION,
    SHOPIFY_BURST_LIMIT,
    SHOPIFY_RATE_LIMIT_PER_SEC,
    SHOPIFY_STORE_URL,
)
from src.product.models import ProductListing


class ShopifyListing:
    """Shopify Admin REST API を使った商品出品クライアント。

    レート制限: 2リクエスト/秒（バースト最大40）を tenacity ではなく
    シンプルな sleep で実装（外部依存を最小限に保つため）。
    """

    def __init__(
        self,
        store_url: str = SHOPIFY_STORE_URL,
        access_token: str = SHOPIFY_ACCESS_TOKEN,
    ) -> None:
        if not store_url or not access_token:
            raise ValueError(
                "SHOPIFY_STORE_URL と SHOPIFY_ACCESS_TOKEN を .env に設定してください。"
            )
        self._base_url = f"https://{store_url}/admin/api/{SHOPIFY_API_VERSION}"
        self._headers = {
            "X-Shopify-Access-Token": access_token,
            "Content-Type": "application/json",
        }
        self._last_request_time: float = 0.0
        self._request_count: int = 0

    async def _rate_limit_wait(self) -> None:
        """レート制限を守るための待機。イベントループをブロックしない。"""
        now = time.monotonic()
        elapsed = now - self._last_request_time
        min_interval = 1.0 / SHOPIFY_RATE_LIMIT_PER_SEC
        if elapsed < min_interval:
            await asyncio.sleep(min_interval - elapsed)
        self._last_request_time = time.monotonic()
        self._request_count += 1

    async def create_product(self, listing: ProductListing) -> dict[str, object]:
        """商品を1件Shopifyに出品する。成功時は作成された商品データを返す。"""
        await self._rate_limit_wait()
        payload = listing.to_shopify_payload()

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self._base_url}/products.json",
                headers=self._headers,
                content=json.dumps(payload),
                timeout=30.0,
            )

        if response.status_code not in (200, 201):
            raise RuntimeError(f"Shopify API エラー {response.status_code}: {response.text[:500]}")

        data: dict[str, object] = response.json()
        if "errors" in data:
            raise RuntimeError(f"Shopify バリデーションエラー: {str(data['errors'])[:500]}")
        return data

    async def create_products_batch(
        self, listings: list[ProductListing]
    ) -> list[dict[str, object]]:
        """複数商品を順番に出品する（並列ではなく順次 — レート制限遵守）。"""
        results = []
        for listing in listings:
            result = await self.create_product(listing)
            results.append(result)
            # バーストカウントが40に近づいたら1秒待機
            if self._request_count % SHOPIFY_BURST_LIMIT == 0:
                await asyncio.sleep(1.0)
        return results
