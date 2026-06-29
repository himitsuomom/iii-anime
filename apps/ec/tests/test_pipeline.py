"""パイプラインのテスト。APIキーなしでMockを使用。"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.listing.shopify import ShopifyListing
from src.pipeline import PipelineResult, ResalePipeline
from src.product.copyright_checker import CopyrightChecker, CopyrightCheckResult
from src.product.generator import ProductGenerator
from src.product.models import Language, Platform, ProductInput, ProductListing

# ---- テスト用フィクスチャ ----


@pytest.fixture
def sample_input() -> ProductInput:
    return ProductInput(
        name="Mountain Sunrise Mug",
        category="Home & Kitchen / Mugs",
        design_concept="Minimalist mountain silhouette at sunrise, orange and purple gradient",
        target_audience="Outdoor enthusiasts, hikers aged 25-45",
        platform=Platform.SHOPIFY,
        language=Language.EN,
    )


@pytest.fixture
def safe_copyright_result() -> CopyrightCheckResult:
    return CopyrightCheckResult(
        is_safe=True,
        risk_level="low",
        issues=[],
        recommendation="出品可能です。",
    )


@pytest.fixture
def unsafe_copyright_result() -> CopyrightCheckResult:
    return CopyrightCheckResult(
        is_safe=False,
        risk_level="high",
        issues=["商標との類似が検出されました"],
        recommendation="デザインを変更してください。",
    )


@pytest.fixture
def sample_listing(sample_input: ProductInput) -> ProductListing:
    return ProductListing(
        title="Mountain Sunrise Coffee Mug",
        description="Start your morning with inspiration.",
        bullet_points=["Premium ceramic", "Dishwasher safe", "11oz capacity", "Great gift", "Vivid print"],
        tags=["hiking mug", "mountain lover"],
        seo_keywords=["hiking coffee mug", "mountain mug"],
        platform=sample_input.platform,
        language=sample_input.language,
    )


def _make_mock_generator(listing: ProductListing) -> ProductGenerator:
    mock_gen = MagicMock(spec=ProductGenerator)
    mock_gen.generate.return_value = listing
    return mock_gen


def _make_mock_checker(result: CopyrightCheckResult) -> CopyrightChecker:
    mock_checker = MagicMock(spec=CopyrightChecker)
    mock_checker.check.return_value = result
    return mock_checker


# ---- ResalePipeline.run のテスト ----


class TestResalePipelineRun:
    async def test_run_skips_listing_when_copyright_unsafe(
        self,
        sample_input: ProductInput,
        unsafe_copyright_result: CopyrightCheckResult,
        sample_listing: ProductListing,
    ) -> None:
        """著作権NGなら listing=None、success=False で早期リターンすること。"""
        mock_gen = _make_mock_generator(sample_listing)
        mock_checker = _make_mock_checker(unsafe_copyright_result)

        pipeline = ResalePipeline(generator=mock_gen, checker=mock_checker)
        result = await pipeline.run(sample_input)

        assert isinstance(result, PipelineResult)
        assert result.listing is None
        assert result.success is False
        assert result.error != ""
        # 著作権NGなので generate は呼ばれないこと
        mock_gen.generate.assert_not_called()

    async def test_run_generates_listing_when_safe(
        self,
        sample_input: ProductInput,
        safe_copyright_result: CopyrightCheckResult,
        sample_listing: ProductListing,
    ) -> None:
        """著作権OKなら listing があり success=True であること。"""
        mock_gen = _make_mock_generator(sample_listing)
        mock_checker = _make_mock_checker(safe_copyright_result)

        pipeline = ResalePipeline(generator=mock_gen, checker=mock_checker)
        result = await pipeline.run(sample_input)

        assert isinstance(result, PipelineResult)
        assert result.listing is not None
        assert result.success is True
        assert result.error == ""
        assert result.listing.title == sample_listing.title
        mock_gen.generate.assert_called_once_with(sample_input)

    async def test_run_stores_copyright_result(
        self,
        sample_input: ProductInput,
        safe_copyright_result: CopyrightCheckResult,
        sample_listing: ProductListing,
    ) -> None:
        """PipelineResult に著作権チェック結果が含まれること。"""
        mock_gen = _make_mock_generator(sample_listing)
        mock_checker = _make_mock_checker(safe_copyright_result)

        pipeline = ResalePipeline(generator=mock_gen, checker=mock_checker)
        result = await pipeline.run(sample_input)

        assert result.copyright_result is safe_copyright_result

    async def test_run_stores_product_input(
        self,
        sample_input: ProductInput,
        safe_copyright_result: CopyrightCheckResult,
        sample_listing: ProductListing,
    ) -> None:
        """PipelineResult に元の ProductInput が含まれること。"""
        mock_gen = _make_mock_generator(sample_listing)
        mock_checker = _make_mock_checker(safe_copyright_result)

        pipeline = ResalePipeline(generator=mock_gen, checker=mock_checker)
        result = await pipeline.run(sample_input)

        assert result.product_input is sample_input

    async def test_run_handles_generator_exception(
        self,
        sample_input: ProductInput,
        safe_copyright_result: CopyrightCheckResult,
    ) -> None:
        """説明文生成中の例外が PipelineResult.error に格納されること。"""
        mock_gen = MagicMock(spec=ProductGenerator)
        mock_gen.generate.side_effect = ValueError("APIエラー")
        mock_checker = _make_mock_checker(safe_copyright_result)

        pipeline = ResalePipeline(generator=mock_gen, checker=mock_checker)
        result = await pipeline.run(sample_input)

        assert result.listing is None
        assert result.success is False
        assert "APIエラー" in result.error

    async def test_run_handles_checker_exception(
        self,
        sample_input: ProductInput,
        sample_listing: ProductListing,
    ) -> None:
        """著作権チェック中の例外が PipelineResult.error に格納されること。"""
        mock_gen = _make_mock_generator(sample_listing)
        mock_checker = MagicMock(spec=CopyrightChecker)
        mock_checker.check.side_effect = ValueError("チェックAPIエラー")

        pipeline = ResalePipeline(generator=mock_gen, checker=mock_checker)
        result = await pipeline.run(sample_input)

        assert result.listing is None
        assert result.success is False
        assert "チェックAPIエラー" in result.error

    async def test_run_uploads_to_shopify_when_client_set(
        self,
        sample_input: ProductInput,
        safe_copyright_result: CopyrightCheckResult,
        sample_listing: ProductListing,
    ) -> None:
        """shopify_client が設定されているとき create_product が呼ばれること。"""
        mock_gen = _make_mock_generator(sample_listing)
        mock_checker = _make_mock_checker(safe_copyright_result)

        shopify_response: dict[str, object] = {"product": {"id": 12345, "title": sample_listing.title}}
        mock_shopify = MagicMock(spec=ShopifyListing)
        mock_shopify.create_product = AsyncMock(return_value=shopify_response)

        pipeline = ResalePipeline(generator=mock_gen, checker=mock_checker, shopify_client=mock_shopify)
        result = await pipeline.run(sample_input)

        assert result.success is True
        assert result.shopify_response == shopify_response
        mock_shopify.create_product.assert_awaited_once_with(sample_listing)

    async def test_run_skips_shopify_when_client_not_set(
        self,
        sample_input: ProductInput,
        safe_copyright_result: CopyrightCheckResult,
        sample_listing: ProductListing,
    ) -> None:
        """shopify_client が None のとき create_product が呼ばれないこと。"""
        mock_gen = _make_mock_generator(sample_listing)
        mock_checker = _make_mock_checker(safe_copyright_result)

        pipeline = ResalePipeline(generator=mock_gen, checker=mock_checker, shopify_client=None)
        result = await pipeline.run(sample_input)

        assert result.success is True
        assert result.shopify_response is None


# ---- ResalePipeline.run_batch のテスト ----


class TestResalePipelineRunBatch:
    async def test_run_batch_processes_all(
        self,
        sample_input: ProductInput,
        safe_copyright_result: CopyrightCheckResult,
        sample_listing: ProductListing,
    ) -> None:
        """バッチで全件処理され、結果リストの長さが入力と一致すること。"""
        mock_gen = _make_mock_generator(sample_listing)
        mock_checker = _make_mock_checker(safe_copyright_result)

        pipeline = ResalePipeline(generator=mock_gen, checker=mock_checker)
        inputs = [sample_input, sample_input, sample_input]
        results = await pipeline.run_batch(inputs)

        assert len(results) == 3
        assert all(isinstance(r, PipelineResult) for r in results)
        assert mock_gen.generate.call_count == 3
        assert mock_checker.check.call_count == 3

    async def test_run_batch_mixed_results(
        self,
        sample_input: ProductInput,
        safe_copyright_result: CopyrightCheckResult,
        unsafe_copyright_result: CopyrightCheckResult,
        sample_listing: ProductListing,
    ) -> None:
        """バッチ内の safe/unsafe が個別に処理されること。"""
        mock_gen = _make_mock_generator(sample_listing)
        mock_checker = MagicMock(spec=CopyrightChecker)
        mock_checker.check.side_effect = [safe_copyright_result, unsafe_copyright_result]

        pipeline = ResalePipeline(generator=mock_gen, checker=mock_checker)
        results = await pipeline.run_batch([sample_input, sample_input])

        assert len(results) == 2
        assert results[0].success is True
        assert results[0].listing is not None
        assert results[1].success is False
        assert results[1].listing is None

    async def test_run_batch_empty_input(
        self,
        safe_copyright_result: CopyrightCheckResult,
        sample_listing: ProductListing,
    ) -> None:
        """空のリストを渡したとき空のリストが返ること。"""
        mock_gen = _make_mock_generator(sample_listing)
        mock_checker = _make_mock_checker(safe_copyright_result)

        pipeline = ResalePipeline(generator=mock_gen, checker=mock_checker)
        results = await pipeline.run_batch([])

        assert results == []
