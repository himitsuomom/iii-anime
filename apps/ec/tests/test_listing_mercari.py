"""MercariListing クラスのユニットテスト。httpx をモックして実際の API を叩かない。"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.listing.mercari import MercariListing
from src.product.models import Language, Platform, ProductListing

# ---- フィクスチャ ----


@pytest.fixture
def listing() -> ProductListing:
    return ProductListing(
        title="テストマグ",
        description="シンプルなマグカップ。",
        bullet_points=["特徴1"],
        tags=["マグ"],
        seo_keywords=["マグ"],
        platform=Platform.MERCARI,
        language=Language.JA,
    )


@pytest.fixture
def long_title_listing() -> ProductListing:
    return ProductListing(
        title="あ" * 41,
        description="説明",
        bullet_points=[],
        tags=[],
        seo_keywords=[],
        platform=Platform.MERCARI,
        language=Language.JA,
    )


@pytest.fixture
def long_desc_listing() -> ProductListing:
    return ProductListing(
        title="タイトル",
        description="あ" * 1001,
        bullet_points=[],
        tags=[],
        seo_keywords=[],
        platform=Platform.MERCARI,
        language=Language.JA,
    )


def _make_mercari_client() -> MercariListing:
    return MercariListing(access_token="test-token")


# ---- TestMercariListingInit ----


class TestMercariListingInit:
    def test_init_raises_without_token(self) -> None:
        """空トークンで ValueError が発生すること。"""
        with pytest.raises(ValueError, match="MERCARI_ACCESS_TOKEN"):
            MercariListing(access_token="")

    def test_init_succeeds_with_valid_token(self) -> None:
        """有効なトークンで正常に初期化されること。"""
        client = _make_mercari_client()
        assert "Authorization" in client._headers


# ---- TestValidateListing ----


class TestValidateListing:
    def test_title_exactly_40_chars_is_ok(self) -> None:
        """タイトルがちょうど40文字の場合はバリデーションが通ること。"""
        listing = ProductListing(
            title="あ" * 40,
            description="説明",
            bullet_points=[],
            tags=[],
            seo_keywords=[],
            platform=Platform.MERCARI,
            language=Language.JA,
        )
        client = _make_mercari_client()
        client._validate_listing(listing)

    def test_title_41_chars_raises(self, long_title_listing: ProductListing) -> None:
        """タイトルが41文字の場合に ValueError が発生すること。"""
        client = _make_mercari_client()
        with pytest.raises(ValueError, match="40文字以内"):
            client._validate_listing(long_title_listing)

    def test_description_exactly_1000_chars_is_ok(self) -> None:
        """説明がちょうど1000文字の場合はバリデーションが通ること。"""
        listing = ProductListing(
            title="タイトル",
            description="あ" * 1000,
            bullet_points=[],
            tags=[],
            seo_keywords=[],
            platform=Platform.MERCARI,
            language=Language.JA,
        )
        client = _make_mercari_client()
        client._validate_listing(listing)

    def test_description_1001_chars_raises(self, long_desc_listing: ProductListing) -> None:
        """説明が1001文字の場合に ValueError が発生すること。"""
        client = _make_mercari_client()
        with pytest.raises(ValueError, match="1000文字以内"):
            client._validate_listing(long_desc_listing)


# ---- TestCreateProduct ----


class TestCreateProduct:
    async def test_create_product_success(self, listing: ProductListing) -> None:
        """POST 成功（200）で dict が返ること。"""
        expected = {"item_id": "m1234567890", "status": "on_sale"}

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = expected

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        client = _make_mercari_client()

        with patch("src.listing.mercari.httpx.AsyncClient", return_value=mock_client):
            result = await client.create_product(listing, price=1500)

        assert result == expected
        mock_client.post.assert_called_once()

    async def test_create_product_url_contains_items_add(
        self, listing: ProductListing
    ) -> None:
        """POST 先 URL に /items/add が含まれること。"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"item_id": "abc"}

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        client = _make_mercari_client()

        with patch("src.listing.mercari.httpx.AsyncClient", return_value=mock_client):
            await client.create_product(listing)

        call_url = mock_client.post.call_args.args[0]
        assert "/items/add" in call_url

    async def test_create_product_raises_on_400(self, listing: ProductListing) -> None:
        """400 エラーで RuntimeError が発生すること。"""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        client = _make_mercari_client()

        with (
            patch("src.listing.mercari.httpx.AsyncClient", return_value=mock_client),
            pytest.raises(RuntimeError, match="400"),
        ):
            await client.create_product(listing)

    async def test_create_product_raises_on_500(self, listing: ProductListing) -> None:
        """500 エラーで RuntimeError が発生すること。"""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        client = _make_mercari_client()

        with (
            patch("src.listing.mercari.httpx.AsyncClient", return_value=mock_client),
            pytest.raises(RuntimeError, match="500"),
        ):
            await client.create_product(listing)

    async def test_create_product_payload_contains_name(
        self, listing: ProductListing
    ) -> None:
        """POSTペイロードに name フィールドが含まれること。"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"item_id": "abc"}

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        client = _make_mercari_client()

        with patch("src.listing.mercari.httpx.AsyncClient", return_value=mock_client):
            await client.create_product(listing, price=2000)

        call_kwargs = mock_client.post.call_args.kwargs
        sent_body = json.loads(call_kwargs["content"])
        assert "name" in sent_body
        assert sent_body["name"] == listing.title

    async def test_create_product_does_not_post_on_validation_failure(
        self, long_title_listing: ProductListing
    ) -> None:
        """バリデーション失敗時は POST が呼ばれないこと。"""
        mock_client = AsyncMock()
        mock_client.post = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        client = _make_mercari_client()

        with (
            patch("src.listing.mercari.httpx.AsyncClient", return_value=mock_client),
            pytest.raises(ValueError),
        ):
            await client.create_product(long_title_listing)

        mock_client.post.assert_not_called()


# ---- TestCreateProductsBatch ----


class TestCreateProductsBatch:
    async def test_create_products_batch_calls_n_times(
        self, listing: ProductListing
    ) -> None:
        """n件のバッチで POST が n 回呼ばれること。"""
        n = 3
        pairs = [(listing, 1000)] * n

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"item_id": "x"}

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        client = _make_mercari_client()

        with patch("src.listing.mercari.httpx.AsyncClient", return_value=mock_client):
            results = await client.create_products_batch(pairs)

        assert len(results) == n
        assert mock_client.post.call_count == n

    async def test_create_products_batch_empty_list(self) -> None:
        """空リストを渡すと空のリストが返ること。"""
        client = _make_mercari_client()
        results = await client.create_products_batch([])
        assert results == []

    async def test_create_products_batch_returns_all_results(
        self, listing: ProductListing
    ) -> None:
        """バッチ結果が全件リストで返ること。"""
        responses = [{"item_id": f"m{i}"} for i in range(2)]
        resp_iter = iter(responses)

        def make_mock() -> MagicMock:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = next(resp_iter)
            return mock_response

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=lambda *_a, **_kw: make_mock())
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        client = _make_mercari_client()

        with patch("src.listing.mercari.httpx.AsyncClient", return_value=mock_client):
            results = await client.create_products_batch(
                [(listing, 1000), (listing, 2000)]
            )

        assert len(results) == 2
        assert results[0]["item_id"] == "m0"
        assert results[1]["item_id"] == "m1"
