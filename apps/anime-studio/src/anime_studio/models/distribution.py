"""Distribution / platform-optimization artifacts (配信最適化)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class TitleCandidate(BaseModel):
    text: str
    hook_archetype: str = ""
    ctr_rationale: str = ""


class ThumbnailSpec(BaseModel):
    concept: str
    focal_point: str = ""
    emotion: str = ""
    text_overlay: str = ""


class PlatformVariant(BaseModel):
    platform: str
    duration_s: int
    aspect_ratio: str = "9:16"
    audio_strategy: str = ""
    caption: str = ""
    hashtags: list[str] = Field(default_factory=list)


class DistributionPlan(BaseModel):
    variants: list[PlatformVariant] = Field(default_factory=list)
    thumbnail: ThumbnailSpec = Field(default_factory=lambda: ThumbnailSpec(concept=""))
    titles: list[TitleCandidate] = Field(default_factory=list)
