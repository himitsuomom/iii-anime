"""Storyboard artifacts (絵コンテ)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Composition(BaseModel):
    rule: str = "rule_of_thirds"
    shot_size: str = "MS"
    notes: str = ""


class CameraMove(BaseModel):
    move_id: str = "static"
    vocab: list[str] = Field(default_factory=list)
    effect: str = ""


class Cut(BaseModel):
    index: int
    beat_id: str
    duration_s: float
    description: str
    composition: Composition = Field(default_factory=Composition)
    camera: CameraMove = Field(default_factory=CameraMove)
    color_mood: str = ""
    lighting: str = ""


class Storyboard(BaseModel):
    cuts: list[Cut] = Field(default_factory=list)
