"""Batch production: run a slate of briefs as a studio would a release schedule."""

from __future__ import annotations

import asyncio
import time
import uuid
from pathlib import Path

import yaml

from ..config import AnimeStudioConfig
from ..models.brief import ProjectBrief
from ..models.edit import EditPlan
from ..models.operations import LedgerEntry
from ..models.qa import QAReport
from ..models.script import CreativeBrief
from ..pipeline.orchestrator import PipelineOutput, run_pipeline
from .ledger import Ledger


def load_slate(path: Path) -> list[ProjectBrief]:
    """Load a slate file: a YAML list, or a mapping with a 'videos' key."""
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    items = data.get("videos", []) if isinstance(data, dict) else data
    briefs: list[ProjectBrief] = []
    for item in items:
        item.setdefault("project_id", f"proj-{int(time.time())}-{uuid.uuid4().hex[:6]}")
        briefs.append(ProjectBrief.model_validate(item))
    return briefs


class BatchRunner:
    def __init__(self, config: AnimeStudioConfig, concurrency: int = 2) -> None:
        self._config = config
        self._concurrency = max(1, concurrency)
        self._ledger = Ledger(config.output_path / "_ledger.json")

    @property
    def ledger(self) -> Ledger:
        return self._ledger

    async def run(self, briefs: list[ProjectBrief]) -> list[LedgerEntry]:
        sem = asyncio.Semaphore(self._concurrency)

        async def one(brief: ProjectBrief) -> LedgerEntry:
            async with sem:
                try:
                    output = await run_pipeline(brief, self._config)
                    entry = _entry_from_output(brief, output)
                except Exception as exc:  # noqa: BLE001 - record failure, keep the batch going
                    entry = LedgerEntry(
                        project_id=brief.project_id, title=brief.title_idea, status="failed", error=str(exc)
                    )
                self._ledger.append(entry)
                return entry

        return await asyncio.gather(*[one(b) for b in briefs])


def _entry_from_output(brief: ProjectBrief, output: PipelineOutput) -> LedgerEntry:
    qa = output.artifacts.get("qa")
    planning = output.artifacts.get("planning")
    editing = output.artifacts.get("editing")
    qa_passed = qa.passed if isinstance(qa, QAReport) else False
    qa_score = _avg_score(qa) if isinstance(qa, QAReport) else None
    return LedgerEntry(
        project_id=brief.project_id,
        title=brief.title_idea,
        status="completed",
        qa_passed=qa_passed,
        qa_score=qa_score,
        hook_archetype=planning.hook_archetype if isinstance(planning, CreativeBrief) else "",
        bpm=editing.bpm if isinstance(editing, EditPlan) else None,
        platforms=list(brief.target_platforms),
        bible_path=str(output.bible_path),
        animatic_path=str(output.animatic_path) if output.animatic_path else None,
    )


def _avg_score(qa: QAReport) -> float | None:
    scores = [g.score for g in qa.gates if g.score is not None]
    return round(sum(scores) / len(scores), 1) if scores else None
