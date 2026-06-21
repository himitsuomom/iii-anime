"""Mock image provider: returns placeholder descriptors (no render)."""

from __future__ import annotations

from ...models.artifacts import ArtifactDescriptor
from ..types import GenSpec


class MockImageProvider:
    name = "mock-image"

    async def generate(self, spec: GenSpec) -> ArtifactDescriptor:
        return ArtifactDescriptor(
            kind="image",
            status="mock",
            uri=None,
            prompt=spec.prompt,
            provider=self.name,
            metadata={"negative_prompt": spec.negative_prompt, **spec.params},
        )
