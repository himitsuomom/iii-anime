"""Per-cut generation prompts (作画・素材生成)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from .artifacts import ArtifactDescriptor


class GenerationPrompt(BaseModel):
    cut_index: int
    positive: str
    negative: str = ""
    animation_principles: list[str] = Field(default_factory=list)
    recommended_tool: str = "AniSora"
    params: dict[str, Any] = Field(default_factory=dict)
    clip: ArtifactDescriptor | None = None


class CutPromptSet(BaseModel):
    prompts: list[GenerationPrompt] = Field(default_factory=list)
