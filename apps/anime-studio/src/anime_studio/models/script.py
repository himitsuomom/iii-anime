"""Planning + script artifacts (企画 / 脚本)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class CreativeBrief(BaseModel):
    """Planning department output: the viral/creative strategy (STEPPS)."""

    concept: str
    primary_platform: str
    emotional_core: str
    hook_archetype: str
    stepps_levers: list[str] = Field(default_factory=list)
    share_trigger: str = ""


class Beat(BaseModel):
    """One beat of the compressed Save-the-Cat Shorts structure."""

    id: str
    label: str
    start_s: float
    end_s: float
    narrative: str
    visual_metaphor: str
    emotion: str


class ScriptArtifact(BaseModel):
    framework: str = "save_the_cat_shorts"
    logline: str = ""
    theme: str = ""
    beats: list[Beat] = Field(default_factory=list)
    silent_storytelling_notes: list[str] = Field(default_factory=list)
