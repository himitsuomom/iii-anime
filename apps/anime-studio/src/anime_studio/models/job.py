"""Job tracking + progress event models (used by the worker for state/stream)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

StageState = Literal["pending", "running", "passed", "revised", "failed"]


class StageStatus(BaseModel):
    stage_id: str
    department: str
    state: StageState = "pending"
    revisions: int = 0
    detail: str = ""


class ProgressEvent(BaseModel):
    project_id: str
    stage_id: str
    state: StageState
    message: str = ""
    meta: dict[str, Any] = Field(default_factory=dict)


class PipelineJob(BaseModel):
    project_id: str
    status: Literal["pending", "running", "completed", "failed"] = "pending"
    stages: list[StageStatus] = Field(default_factory=list)
    output_dir: str = ""
    error: str | None = None
