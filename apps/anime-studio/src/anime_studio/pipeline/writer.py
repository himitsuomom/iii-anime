"""Serialize pipeline artifacts to the output directory."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel

# stage_id -> output filename (relative to the project dir).
_STAGE_FILES = {
    "planning": "creative_brief.json",
    "script": "script.json",
    "character": "character_sheet.json",
    "storyboard": "storyboard.json",
    "production": "cut_prompts.json",
    "editing": "edit_plan.json",
    "qa": "qa_report.json",
    "distribution": "distribution.json",
}


def _dump(model: Any) -> Any:
    if isinstance(model, BaseModel):
        return model.model_dump(mode="json")
    return model


def write_artifacts(project_dir: Path, brief: BaseModel, artifacts: dict[str, Any]) -> list[Path]:
    """Write brief + every stage artifact (+ per-cut files) as JSON. Returns paths."""
    project_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    brief_path = project_dir / "brief.json"
    brief_path.write_text(json.dumps(_dump(brief), ensure_ascii=False, indent=2), encoding="utf-8")
    written.append(brief_path)

    for stage_id, filename in _STAGE_FILES.items():
        if stage_id not in artifacts:
            continue
        path = project_dir / filename
        path.write_text(json.dumps(_dump(artifacts[stage_id]), ensure_ascii=False, indent=2), encoding="utf-8")
        written.append(path)

    # Explode per-cut generation prompts for hand-off to the gen tools.
    production = artifacts.get("production")
    if production is not None:
        cuts_dir = project_dir / "cuts"
        cuts_dir.mkdir(exist_ok=True)
        for prompt in getattr(production, "prompts", []):
            path = cuts_dir / f"cut_{prompt.cut_index:02d}.json"
            path.write_text(json.dumps(_dump(prompt), ensure_ascii=False, indent=2), encoding="utf-8")
            written.append(path)

    # Split distribution by platform for convenience.
    distribution = artifacts.get("distribution")
    if distribution is not None:
        dist_dir = project_dir / "distribution"
        dist_dir.mkdir(exist_ok=True)
        for variant in getattr(distribution, "variants", []):
            path = dist_dir / f"{variant.platform}.json"
            path.write_text(json.dumps(_dump(variant), ensure_ascii=False, indent=2), encoding="utf-8")
            written.append(path)

    return written
