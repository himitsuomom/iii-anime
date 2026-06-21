"""Generic provider artifact descriptor shared across capabilities."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ArtifactDescriptor(BaseModel):
    """A pointer to a (possibly not-yet-rendered) generated asset.

    ``uri`` is ``None`` for mock/stub outputs; a real adapter fills it with a
    path or URL. ``status`` records whether this is a placeholder or a real
    render so the production bible can flag what still needs generating.
    """

    kind: str
    status: Literal["mock", "stub", "rendered"] = "mock"
    uri: str | None = None
    prompt: str = ""
    provider: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
