"""Assemble real per-cut video clips (when available) into the final mp4."""

from __future__ import annotations

from typing import Any

from ..models.artifacts import ArtifactDescriptor
from ..models.edit import EditPlan
from ..models.prompts import CutPromptSet


def rendered_clips(artifacts: dict[str, Any]) -> list[ArtifactDescriptor]:
    """Per-cut clips that a real video provider actually produced, in cut order."""
    production = artifacts.get("production")
    if not isinstance(production, CutPromptSet):
        return []
    clips = [p.clip for p in sorted(production.prompts, key=lambda p: p.cut_index)]
    return [c for c in clips if c is not None and c.status == "rendered" and c.uri]


async def assemble_final_video(artifacts: dict[str, Any], edit_provider: Any) -> ArtifactDescriptor | None:
    """Concatenate real clips via the edit provider. None when there are no clips."""
    clips = rendered_clips(artifacts)
    if not clips:
        return None
    edit = artifacts.get("editing")
    plan = edit if isinstance(edit, EditPlan) else EditPlan()
    result = await edit_provider.assemble(plan, clips)
    return result if result.status == "rendered" else None
