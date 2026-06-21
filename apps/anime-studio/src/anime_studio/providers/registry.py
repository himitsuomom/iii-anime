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
        image=_build_image(cfg),
        video=_build_video(cfg),
        audio=_build_audio(cfg),
        edit=_build_edit(cfg),
    )


def _build_llm(cfg: AnimeStudioConfig) -> LLMProvider:
    mock = MockLLMProvider()
    if cfg.llm.provider == "anthropic":
        return AnthropicLLMProvider(cfg.llm.model, cfg.anthropic_api_key, fallback=mock)
    return mock


def _build_image(cfg: AnimeStudioConfig) -> ImageProvider:
    if cfg.image.provider == "hosted":
        from .hosted.image import HostedImageProvider

        return HostedImageProvider(cfg.image, fallback=MockImageProvider())
    return MockImageProvider()


def _build_video(cfg: AnimeStudioConfig) -> VideoProvider:
    if cfg.video.provider == "hosted":
        from .hosted.video import HostedVideoProvider

        return HostedVideoProvider(cfg.video, fallback=MockVideoProvider())
    return MockVideoProvider()


def _build_audio(cfg: AnimeStudioConfig) -> AudioProvider:
    if cfg.audio.provider == "hosted":
        from .ffmpeg.audio import FfmpegAudioProvider
        from .hosted.audio import HostedAudioProvider

        return HostedAudioProvider(cfg.audio, fallback=FfmpegAudioProvider())
    if cfg.audio.provider == "ffmpeg":
        from .ffmpeg.audio import FfmpegAudioProvider

        return FfmpegAudioProvider()
    return MockAudioProvider()


def _build_edit(cfg: AnimeStudioConfig) -> EditProvider:
    if cfg.edit.provider in ("ffmpeg", "hosted"):
        from .ffmpeg.edit import FfmpegEditProvider

        return FfmpegEditProvider()
    return MockEditProvider()
