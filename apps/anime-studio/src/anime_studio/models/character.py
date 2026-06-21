"""Character design artifacts (設定・キャラデザ)."""

from __future__ import annotations

from pydantic import BaseModel, Field

from .artifacts import ArtifactDescriptor


class CharacterDesign(BaseModel):
    name: str
    role: str
    visual_description: str
    palette: list[str] = Field(default_factory=list)
    # ControlNet/LoRA notes for cross-shot identity consistency.
    consistency_notes: str = ""
    reference_art: list[ArtifactDescriptor] = Field(default_factory=list)


class CharacterSheet(BaseModel):
    characters: list[CharacterDesign] = Field(default_factory=list)
