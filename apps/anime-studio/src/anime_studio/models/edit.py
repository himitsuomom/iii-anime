"""Edit & sound plan artifacts (編集・音響)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class EditSegment(BaseModel):
    cut_index: int
    in_s: float
    out_s: float
    transition: str = "cut"


class AudioCue(BaseModel):
    at_s: float
    kind: str  # "bgm" | "se" | "leitmotif" | "silence"
    description: str
    uri: str | None = None  # set when a real/procedural audio asset was generated


class EditPlan(BaseModel):
    bpm: int = 128
    segments: list[EditSegment] = Field(default_factory=list)
    audio_cues: list[AudioCue] = Field(default_factory=list)
    leitmotif: str = ""
    loop_strategy: str = ""
