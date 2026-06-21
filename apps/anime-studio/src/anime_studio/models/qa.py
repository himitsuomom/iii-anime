"""Quality-assurance artifacts (品質管理 / AniEval-style gates)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class QAGateResult(BaseModel):
    gate: str
    passed: bool
    score: float | None = None
    feedback: str = ""


class QAReport(BaseModel):
    gates: list[QAGateResult] = Field(default_factory=list)
    passed: bool = True
    revision_requested_for: list[str] = Field(default_factory=list)
