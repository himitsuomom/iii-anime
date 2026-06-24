"""generate_prompt / detect_phase のユニットテスト。"""

from __future__ import annotations

from sdlc_prompt_gen.detect.phase_detector import detect_phase
from sdlc_prompt_gen.generators.builder import build_prompt
from sdlc_prompt_gen.phases import get_phase


def test_get_phase_valid():
    spec = get_phase(3)
    assert spec.number == 3
    assert spec.name_en == "Design"
    assert "Triangle" in spec.philosophy


def test_get_phase_out_of_range():
    import pytest

    with pytest.raises(ValueError):
        get_phase(99)


def test_detect_phase_keyword_hit():
    result = detect_phase("このAPIのテストコードを書きたい、カバレッジも確認したい")
    assert result.phase == 6  # テスト・カバレッジ → BEテスト
    assert result.confidence >= 0.6


def test_detect_phase_no_match():
    result = detect_phase("今日の天気はどうですか")
    assert result.phase == 0
    assert result.confidence == 0.0


def test_detect_phase_empty():
    result = detect_phase("")
    assert result.phase == 0


def test_build_prompt_with_template():
    spec = get_phase(3)
    out = build_prompt(spec, project_context="ECサイトの認証機能")
    assert "system_prompt" in out
    assert "user_prompt" in out
    assert "ECサイトの認証機能" in out["user_prompt"]
    # Phase 3 はテンプレートが存在するので template_loaded=True
    assert out["phase_meta"]["template_loaded"] is True


def test_build_prompt_fallback():
    # テンプレート未整備のフェーズ（例: Phase 1）でもフォールバックで動く
    spec = get_phase(1)
    out = build_prompt(spec, project_context="家計簿アプリを作りたい")
    assert "system_prompt" in out
    assert spec.name_ja in out["system_prompt"]


def test_build_prompt_with_prior_artifacts():
    spec = get_phase(3)
    out = build_prompt(
        spec,
        project_context="ECサイト",
        prior_artifacts=["prompts/2026/04/1-ec-concept.md"],
    )
    assert "prior_artifacts" in out["user_prompt"]
    assert "1-ec-concept.md" in out["user_prompt"]
