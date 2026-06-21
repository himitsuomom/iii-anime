"""Hosted-API image provider (Replicate / fal.ai-style async prediction)."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from ...config import ProviderConfig
from ...models.artifacts import ArtifactDescriptor
from ..mock.image import MockImageProvider
from ..types import GenSpec
from ._http import HostedAPIError, await_terminal, download, first_output_url, submit_job


class HostedImageProvider:
    name = "hosted-image"

    def __init__(self, cfg: ProviderConfig, fallback: MockImageProvider | None = None) -> None:
        self._cfg = cfg
        self._fallback = fallback or MockImageProvider()

    async def generate(self, spec: GenSpec) -> ArtifactDescriptor:
        key = self._cfg.api_key
        if not key or not self._cfg.endpoint:
            return await self._fallback.generate(spec)
        try:
            return await asyncio.to_thread(self._generate_sync, spec, key)
        except HostedAPIError:
            return await self._fallback.generate(spec)

    def _generate_sync(self, spec: GenSpec, key: str) -> ArtifactDescriptor:
        payload: dict[str, Any] = {
            "model": self._cfg.model,
            "input": {
                "prompt": spec.prompt,
                "negative_prompt": spec.negative_prompt,
                **self._cfg.params,
                **spec.params,
            },
        }
        if spec.init_image:
            payload["input"]["image"] = spec.init_image
        body = submit_job(self._cfg.endpoint, payload, key, timeout=self._cfg.timeout)
        body = await_terminal(
            body, self._cfg.endpoint, key, timeout=self._cfg.timeout, interval=self._cfg.poll_interval
        )
        url = first_output_url(body)
        out_path = Path(spec.out_path) if spec.out_path else Path("image.png")
        download(url, out_path, timeout=self._cfg.timeout)
        return ArtifactDescriptor(
            kind="image",
            status="rendered",
            uri=str(out_path),
            prompt=spec.prompt,
            provider=self.name,
            metadata={"model": self._cfg.model, "source_url": url},
        )
