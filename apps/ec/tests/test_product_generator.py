"""商品説明文ジェネレーターのテスト。APIキーなしでMockを使用。"""

import json
from unittest.mock import MagicMock, patch

import pytest

from src.product.generator import ProductGenerator, _build_user_prompt
from src.product.models import Language, Platform, ProductInput, ProductListing

# ---- テスト用フィクスチャ ----


@pytest.fixture
def sample_input_en() -> ProductInput:
    return ProductInput(
        name="Mountain Sunrise Mug",
        category="Home & Kitchen / Mugs",
        design_concept="Minimalist mountain silhouette at sunrise, orange and purple gradient",
        target_audience="Outdoor enthusiasts, hikers aged 25-45",
        platform=Platform.SHOPIFY,
        language=Language.EN,
        niche_keywords=["hiking mug", "mountain lover gift", "nature coffee mug"],
    )


@pytest.fixture
def sample_input_ja() -> ProductInput:
    return ProductInput(
        name="山のシルエットマグカップ",
        category="キッチン用品",
        design_concept="ミニマルな山のシルエット、日の出グラデーション",
        target_audience="アウトドア好き、登山愛好家 25-45歳",
        platform=Platform.MERCARI,
        language=Language.JA,
    )


@pytest.fixture
def mock_claude_response() -> dict[str, object]:
    return {
        "title": "Mountain Sunrise Coffee Mug - Hiking Gift for Outdoor Lovers",
        "description": "Start your morning with inspiration. This beautiful mountain sunrise mug features a minimalist design perfect for hikers and nature lovers.",
        "bullet_points": [
            "Premium ceramic construction, dishwasher and microwave safe",
            "Stunning mountain silhouette with vibrant sunrise gradient",
            "Perfect gift for hikers, campers, and outdoor enthusiasts",
            "11oz capacity, comfortable C-handle for easy grip",
            "Wrapped in protective packaging, ready for gifting",
        ],
        "tags": [
            "hiking mug",
            "mountain lover gift",
            "nature coffee mug",
            "outdoor gift",
            "sunrise mug",
            "minimalist mug",
            "hiker gift",
            "camping mug",
            "nature lover",
            "adventure mug",
            "mountain art",
            "coffee lover",
        ],
        "seo_keywords": [
            "hiking coffee mug",
            "mountain lover gift",
            "outdoor enthusiast mug",
            "nature lover coffee cup",
            "hiker gift idea",
            "mountain sunrise mug",
        ],
    }


# ---- _build_user_prompt のテスト ----


class TestBuildUserPrompt:
    def test_includes_product_name(self, sample_input_en: ProductInput) -> None:
        from src.config import PLATFORM_LIMITS

        limits = PLATFORM_LIMITS["shopify"]
        prompt = _build_user_prompt(sample_input_en, limits)
        assert "Mountain Sunrise Mug" in prompt

    def test_includes_niche_keywords(self, sample_input_en: ProductInput) -> None:
        from src.config import PLATFORM_LIMITS

        limits = PLATFORM_LIMITS["shopify"]
        prompt = _build_user_prompt(sample_input_en, limits)
        assert "hiking mug" in prompt

    def test_japanese_instruction_for_ja(self, sample_input_ja: ProductInput) -> None:
        from src.config import PLATFORM_LIMITS

        limits = PLATFORM_LIMITS["mercari"]
        prompt = _build_user_prompt(sample_input_ja, limits)
        assert "日本語" in prompt

    def test_english_instruction_for_en(self, sample_input_en: ProductInput) -> None:
        from src.config import PLATFORM_LIMITS

        limits = PLATFORM_LIMITS["shopify"]
        prompt = _build_user_prompt(sample_input_en, limits)
        assert "Generate in English" in prompt


# ---- ProductGenerator のテスト ----


class TestProductGenerator:
    def test_init_raises_without_api_key(self) -> None:
        with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
            ProductGenerator(api_key="")

    def test_generate_returns_product_listing(
        self,
        sample_input_en: ProductInput,
        mock_claude_response: dict[str, object],
    ) -> None:
        mock_message = MagicMock()
        mock_message.content = [MagicMock(text=json.dumps(mock_claude_response))]

        with patch("anthropic.Anthropic") as mock_anthropic_cls:
            mock_client = mock_anthropic_cls.return_value
            mock_client.messages.create.return_value = mock_message

            gen = ProductGenerator(api_key="test-key")
            result = gen.generate(sample_input_en)

        assert isinstance(result, ProductListing)
        assert result.title == mock_claude_response["title"]
        assert len(result.bullet_points) == 5
        assert result.platform == Platform.SHOPIFY
        assert result.language == Language.EN

    def test_parse_response_strips_code_block(self, sample_input_en: ProductInput) -> None:
        wrapped = f"```json\n{json.dumps({'title': 'T', 'description': 'D', 'bullet_points': ['B'], 'tags': ['t'], 'seo_keywords': ['k']})}\n```"
        result = ProductGenerator._parse_response(wrapped, sample_input_en)
        assert result.title == "T"

    def test_parse_response_raises_on_invalid_json(self, sample_input_en: ProductInput) -> None:
        with pytest.raises(ValueError, match="JSON"):
            ProductGenerator._parse_response("not valid json", sample_input_en)

    def test_generate_batch(
        self,
        sample_input_en: ProductInput,
        mock_claude_response: dict[str, object],
    ) -> None:
        mock_message = MagicMock()
        mock_message.content = [MagicMock(text=json.dumps(mock_claude_response))]

        with patch("anthropic.Anthropic") as mock_anthropic_cls:
            mock_client = mock_anthropic_cls.return_value
            mock_client.messages.create.return_value = mock_message

            gen = ProductGenerator(api_key="test-key")
            results = gen.generate_batch([sample_input_en, sample_input_en])

        assert len(results) == 2
        assert mock_client.messages.create.call_count == 2


# ---- ProductListing.to_shopify_payload のテスト ----


class TestProductListingPayload:
    @pytest.fixture
    def listing(self, mock_claude_response: dict[str, object]) -> ProductListing:
        return ProductListing(
            title=str(mock_claude_response["title"]),
            description=str(mock_claude_response["description"]),
            bullet_points=list(mock_claude_response["bullet_points"]),  # type: ignore[arg-type]
            tags=list(mock_claude_response["tags"]),  # type: ignore[arg-type]
            seo_keywords=list(mock_claude_response["seo_keywords"]),  # type: ignore[arg-type]
            platform=Platform.SHOPIFY,
            language=Language.EN,
        )

    def test_to_shopify_payload_has_required_keys(self, listing: ProductListing) -> None:
        payload = listing.to_shopify_payload()
        assert "product" in payload
        product = payload["product"]
        assert "title" in product
        assert "body_html" in product
        assert "tags" in product

    def test_to_amazon_payload_has_required_keys(self, listing: ProductListing) -> None:
        payload = listing.to_amazon_payload()
        assert "title" in payload
        assert "description" in payload
        assert "bullet_points" in payload
        assert "keywords" in payload

    def test_to_amazon_payload_bullet_points_capped_at_5(self, listing: ProductListing) -> None:
        listing.bullet_points = ["bp"] * 10
        payload = listing.to_amazon_payload()
        assert len(payload["bullet_points"]) <= 5
