"""Provider registry: build the capability bundle from config."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from ..config import AnimeStudioConfig
from .anthropic.llm import AnthropicLLMProvider
from .base import AudioProvider, EditProvider, ImageProvider, LLMProvider, VideoProvider
from .mock import (
    MockAudioProvider,
    MockEditProvider,
    MockImageProvider,
    MockLLMProvider,
    MockVideoProvider,
)


class ProviderBundle(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    llm: LLMProvider
    image: ImageProvider
    video: VideoProvider
    audio: AudioProvider
    edit: EditProvider


def build_providers(cfg: AnimeStudioConfig) -> ProviderBundle:
    return ProviderBundle(
        llm=_build_llm(cfg),
        image=MockImageProvider(),
        video=MockVideoProvider(),
        audio=MockAudioProvider(),
        edit=MockEditProvider(),
    )


def _build_llm(cfg: AnimeStudioConfig) -> LLMProvider:
    mock = MockLLMProvider()
    if cfg.llm.provider == "anthropic":
        return AnthropicLLMProvider(cfg.llm.model, cfg.anthropic_api_key, fallback=mock)
    return mock
