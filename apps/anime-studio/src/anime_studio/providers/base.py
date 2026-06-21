"""Provider-adapter contracts (the swappable seam for real AI services).

All capabilities are Protocols so a real adapter only needs to match the shape —
no inheritance. Today only mock + an Anthropic LLM adapter are wired; real
image/video/audio/edit adapters slot into the registry later without touching
the agents.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from ..models.artifacts import ArtifactDescriptor
from ..models.edit import EditPlan
from .types import GenSpec, LLMMessage, LLMResponse


@runtime_checkable
class LLMProvider(Protocol):
    name: str

    async def complete(
        self,
        messages: list[LLMMessage],
        *,
        system: str | None = None,
        max_tokens: int = 2048,
        temperature: float = 0.7,
    ) -> LLMResponse: ...


@runtime_checkable
class ImageProvider(Protocol):
    name: str

    async def generate(self, spec: GenSpec) -> ArtifactDescriptor: ...


@runtime_checkable
class VideoProvider(Protocol):
    name: str
    supports_render: bool

    async def generate(self, spec: GenSpec) -> ArtifactDescriptor: ...


@runtime_checkable
class AudioProvider(Protocol):
    name: str

    async def generate_bgm(self, spec: GenSpec) -> ArtifactDescriptor: ...

    async def generate_se(self, spec: GenSpec) -> ArtifactDescriptor: ...


@runtime_checkable
class EditProvider(Protocol):
    name: str
    supports_render: bool

    async def assemble(self, edit_plan: EditPlan, clips: list[ArtifactDescriptor]) -> ArtifactDescriptor: ...
