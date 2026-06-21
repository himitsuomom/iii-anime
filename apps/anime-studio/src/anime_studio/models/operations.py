"""Models for the studio's operations layer (ledger, metrics, feedback)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class LedgerEntry(BaseModel):
    """One row of the production ledger — the company's record of a video."""

    project_id: str
    title: str
    status: str = "completed"  # "completed" | "failed"
    qa_passed: bool = False
    qa_score: float | None = None
    hook_archetype: str = ""
    bpm: int | None = None
    platforms: list[str] = Field(default_factory=list)
    bible_path: str = ""
    animatic_path: str | None = None
    error: str | None = None


class VideoMetrics(BaseModel):
    """Post-publish performance signals fed back into planning."""

    project_id: str
    platform: str
    retention_pct: float = 0.0
    completion_pct: float = 0.0
    views: int = 0


class FeedbackBias(BaseModel):
    """What the feedback loop recommends biasing the next slate toward."""

    preferred_hook: str | None = None
    preferred_platform: str | None = None
    preferred_bpm: int | None = None
    sample_size: int = 0
