"""Mock audio provider: returns placeholder BGM/SE descriptors."""

from __future__ import annotations

from ...models.artifacts import ArtifactDescriptor
from ..types import GenSpec


class MockAudioProvider:
    name = "mock-audio"

    async def generate_bgm(self, spec: GenSpec) -> ArtifactDescriptor:
        return ArtifactDescriptor(
            kind="bgm", status="mock", uri=None, prompt=spec.prompt, provider=self.name, metadata=spec.params
        )

    async def generate_se(self, spec: GenSpec) -> ArtifactDescriptor:
        return ArtifactDescriptor(
            kind="se", status="mock", uri=None, prompt=spec.prompt, provider=self.name, metadata=spec.params
        )
