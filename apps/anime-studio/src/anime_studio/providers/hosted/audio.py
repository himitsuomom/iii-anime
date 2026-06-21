"""Hosted-API audio provider (BGM/SE), degrading to procedural ffmpeg audio."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from ...config import ProviderConfig
from ...models.artifacts import ArtifactDescriptor
from ..ffmpeg.audio import FfmpegAudioProvider
from ..types import GenSpec
from ._http import HostedAPIError, await_terminal, download, first_output_url, submit_job


class HostedAudioProvider:
    name = "hosted-audio"

    def __init__(self, cfg: ProviderConfig, fallback: FfmpegAudioProvider | None = None) -> None:
        self._cfg = cfg
        self._fallback = fallback or FfmpegAudioProvider()

    async def generate_bgm(self, spec: GenSpec) -> ArtifactDescriptor:
        return await self._generate(spec, "bgm")

    async def generate_se(self, spec: GenSpec) -> ArtifactDescriptor:
        return await self._generate(spec, "se")

    async def _generate(self, spec: GenSpec, kind: str) -> ArtifactDescriptor:
        key = self._cfg.api_key
        if not key or not self._cfg.endpoint:
            return await self._fallback_for(spec, kind)
        try:
            return await asyncio.to_thread(self._generate_sync, spec, key, kind)
        except HostedAPIError:
            return await self._fallback_for(spec, kind)

    async def _fallback_for(self, spec: GenSpec, kind: str) -> ArtifactDescriptor:
        if kind == "bgm":
            return await self._fallback.generate_bgm(spec)
        return await self._fallback.generate_se(spec)

    def _generate_sync(self, spec: GenSpec, key: str, kind: str) -> ArtifactDescriptor:
        payload: dict[str, Any] = {
            "model": self._cfg.model,
            "input": {"prompt": spec.prompt, "duration": spec.params.get("duration_s"), **self._cfg.params},
        }
        body = submit_job(self._cfg.endpoint, payload, key, timeout=self._cfg.timeout)
        body = await_terminal(
            body, self._cfg.endpoint, key, timeout=self._cfg.timeout, interval=self._cfg.poll_interval
        )
        url = first_output_url(body)
        out_path = Path(spec.out_path) if spec.out_path else Path(f"{kind}.wav")
        download(url, out_path, timeout=self._cfg.timeout)
        return ArtifactDescriptor(
            kind=kind, status="rendered", uri=str(out_path), provider=self.name,
            prompt=spec.prompt, metadata={"model": self._cfg.model, "source_url": url},
        )
