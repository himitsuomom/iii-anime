from __future__ import annotations

import pytest

from anime_studio.providers.anthropic.llm import AnthropicLLMProvider
from anime_studio.providers.mock import MockLLMProvider, MockVideoProvider
from anime_studio.providers.types import GenSpec, LLMMessage


async def test_mock_llm_is_deterministic() -> None:
    llm = MockLLMProvider()
    msg = [LLMMessage(content="beat hook for a sheep")]
    a = await llm.complete(msg)
    b = await llm.complete(msg)
    assert a.text == b.text
    assert a.mocked is True


async def test_mock_video_is_stub() -> None:
    video = MockVideoProvider()
    assert video.supports_render is False
    art = await video.generate(GenSpec(kind="video", prompt="a sheep runs"))
    assert art.status == "stub"
    assert art.uri is None


async def test_anthropic_falls_back_without_key() -> None:
    llm = AnthropicLLMProvider(model="claude-x", api_key=None)
    resp = await llm.complete([LLMMessage(content="hello")])
    assert resp.mocked is True


async def test_anthropic_falls_back_on_error(monkeypatch: pytest.MonkeyPatch) -> None:
    llm = AnthropicLLMProvider(model="claude-x", api_key="sk-test")

    class Boom:
        class messages:
            @staticmethod
            async def create(**_: object) -> object:
                raise RuntimeError("network down")

    llm._client = Boom()  # type: ignore[attr-defined]
    resp = await llm.complete([LLMMessage(content="hello")])
    assert resp.mocked is True
