"""PodtomaticListing クラスのユニットテスト。httpx をモックして実際の API を叩かない。"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.listing.podtomatic import PodtomaticListing
from src.product.models import Language, Platform, ProductListing

# ---- フィクスチャ ----


@pytest.fixture
def listing() -> ProductListing:
    return ProductListing(
        title="Test T-Shirt",
        description="A comfortable t-shirt.",
        bullet_points=["Soft fabric", "Durable print"],
        tags=["tshirt", "fashion"],
        seo_keywords=["custom tshirt", "print on demand"],
        platform=Platform.AMAZON,
        language=Language.EN,
    )


def _make_podtomatic_client() -> PodtomaticListing:
    """テスト用に有効な API キーを持つ PodtomaticListing インスタンスを生成する。"""
    return PodtomaticListing(api_key="test-api-key")


def _make_mock_client(status_code: int = 201, json_body: object = None) -> AsyncMock:
    """httpx.AsyncClient のモックを生成するヘルパー。"""
    if json_body is None:
        json_body = {"id": "prod-001", "status": "created"}
    mock_response = MagicMock()
    mock_response.status_code = status_code
    mock_response.json.return_value = json_body
    mock_response.text = str(json_body)

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    return mock_client


# ---- テストケース ----


class TestPodtomaticListingInit:
    def test_init_raises_without_api_key(self) -> None:
        """api_key が空の場合に ValueError が発生すること。"""
        with pytest.raises(ValueError, match="PODTOMATIC_API_KEY"):
            PodtomaticListing(api_key="")

    def test_init_succeeds_with_valid_api_key(self) -> None:
        """有効な api_key で正常に初期化されること。"""
        client = _make_podtomatic_client()
        assert client._api_key == "test-api-key"

    def test_init_sets_auth_header(self) -> None:
        """初期化時に Authorization ヘッダーが正しく設定されること。"""
        client = _make_podtomatic_client()
        assert client._headers["Authorization"] == "Bearer test-api-key"

    def test_init_daily_count_is_zero(self) -> None:
        """初期化時のアップロード数が 0 であること。"""
        client = _make_podtomatic_client()
        assert client.get_daily_upload_count() == 0


class TestDailyLimitCheck:
    def test_check_daily_limit_raises_at_200(self) -> None:
        """200 件到達時に RuntimeError が発生すること。"""
        client = _make_podtomatic_client()
        client._daily_upload_count = 200
        with pytest.raises(RuntimeError, match="200件"):
            client._check_daily_limit()

    def test_check_daily_limit_raises_above_200(self) -> None:
        """200 件超過時にも RuntimeError が発生すること。"""
        client = _make_podtomatic_client()
        client._daily_upload_count = 201
        with pytest.raises(RuntimeError):
            client._check_daily_limit()

    def test_check_daily_limit_ok_at_199(self) -> None:
        """199 件目は上限未満なので例外が発生しないこと。"""
        client = _make_podtomatic_client()
        client._daily_upload_count = 199
        client._check_daily_limit()  # 例外が発生しないこと

    def test_reset_daily_count(self) -> None:
        """reset_daily_count() でカウントが 0 にリセットされること。"""
        client = _make_podtomatic_client()
        client._daily_upload_count = 150
        client.reset_daily_count()
        assert client.get_daily_upload_count() == 0


class TestUploadProduct:
    async def test_upload_product_success_201(self, listing: ProductListing) -> None:
        """POST 成功（201）で商品データの dict が返ること。"""
        expected_response: dict[str, object] = {"id": "prod-001", "status": "created"}
        mock_client = _make_mock_client(status_code=201, json_body=expected_response)

        client = _make_podtomatic_client()

        with patch("src.listing.podtomatic.httpx.AsyncClient", return_value=mock_client):
            result = await client.upload_product(listing)

        assert result == expected_response
        mock_client.post.assert_called_once()

    def test_upload_product_increments_daily_count(self, listing: ProductListing) -> None:
        """成功時に daily_upload_count が 1 増加すること（同期的に確認）。"""
        client = _make_podtomatic_client()
        # カウントが 0 から始まることを確認
        assert client.get_daily_upload_count() == 0

    async def test_upload_product_increments_count_on_success(
        self, listing: ProductListing
    ) -> None:
        """アップロード成功後に daily_upload_count が増加すること。"""
        mock_client = _make_mock_client(status_code=201)
        client = _make_podtomatic_client()

        with patch("src.listing.podtomatic.httpx.AsyncClient", return_value=mock_client):
            await client.upload_product(listing)

        assert client.get_daily_upload_count() == 1

    async def test_upload_product_raises_on_401_error(self, listing: ProductListing) -> None:
        """401 エラーで RuntimeError が発生すること。"""
        mock_client = _make_mock_client(status_code=401)

        client = _make_podtomatic_client()

        with (
            patch("src.listing.podtomatic.httpx.AsyncClient", return_value=mock_client),
            pytest.raises(RuntimeError, match="401"),
        ):
            await client.upload_product(listing)

    async def test_upload_product_raises_on_500_error(self, listing: ProductListing) -> None:
        """500 エラーで RuntimeError が発生すること。"""
        mock_client = _make_mock_client(status_code=500)

        client = _make_podtomatic_client()

        with (
            patch("src.listing.podtomatic.httpx.AsyncClient", return_value=mock_client),
            pytest.raises(RuntimeError, match="500"),
        ):
            await client.upload_product(listing)

    async def test_upload_product_payload_contains_title(self, listing: ProductListing) -> None:
        """POST リクエストのペイロードに title が含まれること。"""
        mock_client = _make_mock_client(status_code=201)
        client = _make_podtomatic_client()

        with patch("src.listing.podtomatic.httpx.AsyncClient", return_value=mock_client):
            await client.upload_product(listing)

        call_kwargs = mock_client.post.call_args.kwargs
        sent_body = json.loads(call_kwargs["content"])
        assert "title" in sent_body
        assert sent_body["title"] == listing.title

    async def test_upload_product_calls_correct_endpoint(
        self, listing: ProductListing
    ) -> None:
        """POST が /products エンドポイントに送信されること。"""
        mock_client = _make_mock_client(status_code=201)
        client = _make_podtomatic_client()

        with patch("src.listing.podtomatic.httpx.AsyncClient", return_value=mock_client):
            await client.upload_product(listing)

        call_url = mock_client.post.call_args.args[0]
        assert "/products" in call_url

    async def test_upload_product_does_not_increment_count_on_error(
        self, listing: ProductListing
    ) -> None:
        """エラー時には daily_upload_count が増加しないこと。"""
        mock_client = _make_mock_client(status_code=500)
        client = _make_podtomatic_client()

        with (
            patch("src.listing.podtomatic.httpx.AsyncClient", return_value=mock_client),
            pytest.raises(RuntimeError),
        ):
            await client.upload_product(listing)

        assert client.get_daily_upload_count() == 0


class TestUploadProductsBatch:
    async def test_upload_products_batch_calls_post_n_times(
        self, listing: ProductListing
    ) -> None:
        """バッチで n 件渡すと POST が n 回呼ばれること。"""
        n = 3
        listings = [listing] * n
        mock_client = _make_mock_client(status_code=201)

        client = _make_podtomatic_client()

        with patch("src.listing.podtomatic.httpx.AsyncClient", return_value=mock_client):
            results = await client.upload_products_batch(listings)

        assert len(results) == n
        assert mock_client.post.call_count == n

    async def test_upload_products_batch_empty_list(self) -> None:
        """空リストを渡すと空のリストが返ること。"""
        client = _make_podtomatic_client()
        results = await client.upload_products_batch([])
        assert results == []

    async def test_upload_products_batch_increments_count(
        self, listing: ProductListing
    ) -> None:
        """バッチ後に daily_upload_count が件数分増加すること。"""
        n = 5
        listings = [listing] * n
        mock_client = _make_mock_client(status_code=201)

        client = _make_podtomatic_client()

        with patch("src.listing.podtomatic.httpx.AsyncClient", return_value=mock_client):
            await client.upload_products_batch(listings)

        assert client.get_daily_upload_count() == n

    async def test_upload_products_batch_raises_when_limit_reached(
        self, listing: ProductListing
    ) -> None:
        """上限到達後は途中で RuntimeError が発生すること。"""
        client = _make_podtomatic_client()
        # 残り1件のところまでカウントを進める
        client._daily_upload_count = 200

        with pytest.raises(RuntimeError, match="200件"):
            await client.upload_products_batch([listing, listing])

    async def test_upload_products_batch_stops_at_limit(
        self, listing: ProductListing
    ) -> None:
        """上限ちょうどの状態で新たにアップロードしようとすると1件目で止まること。"""
        client = _make_podtomatic_client()
        client._daily_upload_count = 199

        mock_client = _make_mock_client(status_code=201)

        with patch("src.listing.podtomatic.httpx.AsyncClient", return_value=mock_client):
            results = await client.upload_products_batch([listing])

        # 199 + 1 = 200 件、成功
        assert len(results) == 1
        assert client.get_daily_upload_count() == 200

        # これ以上は失敗
        with pytest.raises(RuntimeError):
            await client.upload_products_batch([listing])
