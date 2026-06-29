"""ShopifyListing クラスのユニットテスト。httpx をモックして実際の API を叩かない。"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.listing.shopify import ShopifyListing
from src.product.models import Language, Platform, ProductListing

# ---- フィクスチャ ----


@pytest.fixture
def listing() -> ProductListing:
    return ProductListing(
        title="Test Mug",
        description="A mug.",
        bullet_points=["feature 1"],
        tags=["mug"],
        seo_keywords=["mug"],
        platform=Platform.SHOPIFY,
        language=Language.EN,
    )


def _make_shopify_client() -> ShopifyListing:
    """テスト用に有効な認証情報を持つ ShopifyListing インスタンスを生成する。"""
    return ShopifyListing(
        store_url="test-store.myshopify.com",
        access_token="test-token",
    )


# ---- テストケース ----


class TestShopifyListingInit:
    def test_init_raises_without_credentials(self) -> None:
        """URL/トークン未設定時に ValueError が発生すること。"""
        with pytest.raises(ValueError, match="SHOPIFY_STORE_URL"):
            ShopifyListing(store_url="", access_token="")

    def test_init_raises_without_store_url(self) -> None:
        """store_url が空の場合に ValueError が発生すること。"""
        with pytest.raises(ValueError):
            ShopifyListing(store_url="", access_token="valid-token")

    def test_init_raises_without_access_token(self) -> None:
        """access_token が空の場合に ValueError が発生すること。"""
        with pytest.raises(ValueError):
            ShopifyListing(store_url="test-store.myshopify.com", access_token="")

    def test_init_succeeds_with_valid_credentials(self) -> None:
        """有効な認証情報で正常に初期化されること。"""
        client = _make_shopify_client()
        assert client._base_url.startswith("https://test-store.myshopify.com")


class TestCreateProduct:
    async def test_create_product_success(self, listing: ProductListing) -> None:
        """POST 成功（201）で商品データの dict が返ること。"""
        expected_response = {"product": {"id": 123, "title": "Test Mug"}}

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = expected_response

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        client = _make_shopify_client()

        with patch("src.listing.shopify.httpx.AsyncClient", return_value=mock_client), patch(
            "src.listing.shopify.asyncio.sleep"
        ):
            result = await client.create_product(listing)

        assert result == expected_response
        mock_client.post.assert_called_once()
        call_url = mock_client.post.call_args.args[0]
        assert "products.json" in call_url

    async def test_create_product_success_200(self, listing: ProductListing) -> None:
        """POST 成功（200）でも dict が返ること。"""
        expected_response = {"product": {"id": 456, "title": "Test Mug"}}

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = expected_response

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        client = _make_shopify_client()

        with patch("src.listing.shopify.httpx.AsyncClient", return_value=mock_client), patch(
            "src.listing.shopify.asyncio.sleep"
        ):
            result = await client.create_product(listing)

        assert result == expected_response

    async def test_create_product_raises_on_api_error(self, listing: ProductListing) -> None:
        """422 エラーで RuntimeError が発生すること。"""
        mock_response = MagicMock()
        mock_response.status_code = 422
        mock_response.text = "Unprocessable Entity: title is required"

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        client = _make_shopify_client()

        with (
            patch("src.listing.shopify.httpx.AsyncClient", return_value=mock_client),
            patch("src.listing.shopify.time.sleep"),
            pytest.raises(RuntimeError, match="422"),
        ):
            await client.create_product(listing)

    async def test_create_product_raises_on_500_error(self, listing: ProductListing) -> None:
        """500 エラーで RuntimeError が発生すること。"""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        client = _make_shopify_client()

        with (
            patch("src.listing.shopify.httpx.AsyncClient", return_value=mock_client),
            patch("src.listing.shopify.time.sleep"),
            pytest.raises(RuntimeError, match="500"),
        ):
            await client.create_product(listing)

    async def test_create_product_raises_on_error_body_with_200(self, listing: ProductListing) -> None:
        """200 でも errors キーがある場合に RuntimeError が発生すること。"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"errors": {"title": ["can't be blank"]}}

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        client = _make_shopify_client()

        with (
            patch("src.listing.shopify.httpx.AsyncClient", return_value=mock_client),
            patch("src.listing.shopify.asyncio.sleep"),
            pytest.raises(RuntimeError, match="バリデーション"),
        ):
            await client.create_product(listing)

    async def test_create_product_sends_correct_payload(self, listing: ProductListing) -> None:
        """POST リクエストに正しい Shopify ペイロードが含まれること。"""
        expected_payload = listing.to_shopify_payload()

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"product": {"id": 789}}

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        client = _make_shopify_client()

        with patch("src.listing.shopify.httpx.AsyncClient", return_value=mock_client), patch(
            "src.listing.shopify.asyncio.sleep"
        ):
            await client.create_product(listing)

        call_kwargs = mock_client.post.call_args.kwargs
        sent_body = json.loads(call_kwargs["content"])
        assert sent_body == expected_payload


class TestCreateProductsBatch:
    async def test_create_products_batch_calls_create_n_times(
        self, listing: ProductListing
    ) -> None:
        """バッチで n 件の商品を渡すと POST が n 回呼ばれること。"""
        n = 3
        listings = [listing] * n

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"product": {"id": 1}}

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        client = _make_shopify_client()

        with patch("src.listing.shopify.httpx.AsyncClient", return_value=mock_client), patch(
            "src.listing.shopify.asyncio.sleep"
        ), patch("src.listing.shopify.asyncio.sleep"):
            results = await client.create_products_batch(listings)

        assert len(results) == n
        assert mock_client.post.call_count == n

    async def test_create_products_batch_returns_all_results(
        self, listing: ProductListing
    ) -> None:
        """バッチ結果が全件リストで返ること。"""
        n = 2
        listings = [listing] * n
        responses = [{"product": {"id": i + 1}} for i in range(n)]
        response_iter = iter(responses)

        def make_mock_response() -> MagicMock:
            mock_response = MagicMock()
            mock_response.status_code = 201
            mock_response.json.return_value = next(response_iter)
            return mock_response

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=lambda *_a, **_kw: make_mock_response())
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        client = _make_shopify_client()

        with patch("src.listing.shopify.httpx.AsyncClient", return_value=mock_client), patch(
            "src.listing.shopify.asyncio.sleep"
        ), patch("src.listing.shopify.asyncio.sleep"):
            results = await client.create_products_batch(listings)

        assert len(results) == n
        ids = [r["product"]["id"] for r in results]  # type: ignore[index]
        assert ids == [1, 2]

    async def test_create_products_batch_empty_list(self) -> None:
        """空リストを渡すと空のリストが返ること。"""
        client = _make_shopify_client()

        with patch("src.listing.shopify.time.sleep"), patch(
            "src.listing.shopify.asyncio.sleep"
        ):
            results = await client.create_products_batch([])

        assert results == []
