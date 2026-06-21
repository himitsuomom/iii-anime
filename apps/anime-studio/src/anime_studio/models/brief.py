"""The input contract: a project brief describing the video to produce."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ProjectBrief(BaseModel):
    """What the 'client' hands the studio. The only required human input."""

    project_id: str
    title_idea: str
    logline: str
    target_platforms: list[str] = Field(default_factory=lambda: ["youtube_shorts"])
    target_duration_s: int = 60
    tone: str = "heartwarming"
    genre: str = "silent children's comedy"
    audience: str = "children and parents"
    constraints: dict[str, Any] = Field(default_factory=dict)
