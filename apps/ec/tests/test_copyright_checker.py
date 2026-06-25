"""著作権チェッカーのテスト。APIキーなしでMockを使用。"""

import json
from unittest.mock import MagicMock, patch

import pytest

from src.product.copyright_checker import CopyrightChecker, CopyrightCheckResult

# ---- テスト用フィクスチャ ----


@pytest.fixture
def safe_response() -> dict[str, object]:
    return {
        "is_safe": True,
        "risk_level": "low",
        "issues": [],
        "recommendation": "問題なし。出品可能です。",
    }


@pytest.fixture
def unsafe_response() -> dict[str, object]:
    return {
        "is_safe": False,
        "risk_level": "high",
        "issues": [
            "商標登録されたキャラクターに類似している可能性があります",
            "著名ブランドのロゴと酷似した要素が含まれています",
        ],
        "recommendation": "デザインを変更してから再評価してください。",
    }


def _make_mock_message(response_dict: dict[str, object]) -> MagicMock:
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text=json.dumps(response_dict))]
    return mock_message


# ---- CopyrightChecker のテスト ----


class TestCopyrightChecker:
    def test_init_raises_without_api_key(self) -> None:
        with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
            CopyrightChecker(api_key="")

    def test_check_returns_safe_for_generic_design(
        self,
        safe_response: dict[str, object],
    ) -> None:
        """一般的なデザインは safe と判定されること。"""
        mock_message = _make_mock_message(safe_response)

        with patch("anthropic.Anthropic") as mock_anthropic_cls:
            mock_client = mock_anthropic_cls.return_value
            mock_client.messages.create.return_value = mock_message

            checker = CopyrightChecker(api_key="test-key")
            result = checker.check(
                design_description="シンプルな幾何学模様。円と三角形の組み合わせ。",
                product_name="ジオメトリックデザインマグカップ",
            )

        assert isinstance(result, CopyrightCheckResult)
        assert result.is_safe is True
        assert result.risk_level == "low"
        assert result.issues == []
        assert "出品可能" in result.recommendation

    def test_check_returns_unsafe_for_trademark(
        self,
        unsafe_response: dict[str, object],
    ) -> None:
        """商標的な表現は unsafe と判定されること。"""
        mock_message = _make_mock_message(unsafe_response)

        with patch("anthropic.Anthropic") as mock_anthropic_cls:
            mock_client = mock_anthropic_cls.return_value
            mock_client.messages.create.return_value = mock_message

            checker = CopyrightChecker(api_key="test-key")
            result = checker.check(
                design_description="赤いスーパーヒーローの仮面とマント。有名なコミックキャラクターに類似。",
                product_name="スーパーヒーローTシャツ",
            )

        assert isinstance(result, CopyrightCheckResult)
        assert result.is_safe is False
        assert result.risk_level == "high"
        assert len(result.issues) > 0
        assert result.recommendation != ""

    def test_check_calls_api_with_correct_content(
        self,
        safe_response: dict[str, object],
    ) -> None:
        """APIが正しい引数で呼ばれること。"""
        mock_message = _make_mock_message(safe_response)

        with patch("anthropic.Anthropic") as mock_anthropic_cls:
            mock_client = mock_anthropic_cls.return_value
            mock_client.messages.create.return_value = mock_message

            checker = CopyrightChecker(api_key="test-key")
            checker.check(
                design_description="抽象的な水彩画パターン",
                product_name="水彩画トートバッグ",
            )

        call_kwargs = mock_client.messages.create.call_args.kwargs
        assert call_kwargs["messages"][0]["role"] == "user"
        assert "水彩画トートバッグ" in call_kwargs["messages"][0]["content"]
        assert "抽象的な水彩画パターン" in call_kwargs["messages"][0]["content"]


# ---- _parse_response のテスト ----


class TestParseResponse:
    def test_parse_valid_json_returns_result(self) -> None:
        raw = json.dumps(
            {
                "is_safe": True,
                "risk_level": "low",
                "issues": [],
                "recommendation": "OK",
            }
        )
        result = CopyrightChecker._parse_response(raw)
        assert result.is_safe is True
        assert result.risk_level == "low"

    def test_parse_strips_code_block(self) -> None:
        data = {"is_safe": False, "risk_level": "medium", "issues": ["x"], "recommendation": "y"}
        wrapped = f"```json\n{json.dumps(data)}\n```"
        result = CopyrightChecker._parse_response(wrapped)
        assert result.is_safe is False
        assert result.risk_level == "medium"

    def test_parse_invalid_json_raises(self) -> None:
        """JSON不正時は ValueError が送出されること。"""
        with pytest.raises(ValueError, match="JSON"):
            CopyrightChecker._parse_response("これはJSONではありません")

    def test_parse_missing_fields_uses_defaults(self) -> None:
        """フィールド欠損時はデフォルト値を使うこと。"""
        raw = json.dumps({})
        result = CopyrightChecker._parse_response(raw)
        assert result.is_safe is False
        assert result.risk_level == "high"
        assert result.issues == []
        assert result.recommendation == ""
