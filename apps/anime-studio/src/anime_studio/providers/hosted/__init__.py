"""Hosted-API provider adapters (degrade to mock/ffmpeg when unavailable)."""

from .image import HostedImageProvider

__all__ = ["HostedImageProvider"]
