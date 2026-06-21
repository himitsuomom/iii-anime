"""Mock video provider: returns stub descriptors (real render is a later seam)."""

from __future__ import annotations

from ...models.artifacts import ArtifactDescriptor
from ..types import GenSpec


class MockVideoProvider:
    name = "mock-video"
    supports_render = False

    async def generate(self, spec: GenSpec) -> ArtifactDescriptor:
        return ArtifactDescriptor(
            kind="video",
            status="stub",
            uri=None,
            prompt=spec.prompt,
            provider=self.name,
            metadata={"recommended_tool": spec.params.get("recommended_tool"), **spec.params},
        )
