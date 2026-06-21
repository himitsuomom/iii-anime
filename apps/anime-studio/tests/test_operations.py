from __future__ import annotations

import json
from pathlib import Path

from anime_studio.config import AnimeStudioConfig
from anime_studio.models.brief import ProjectBrief
from anime_studio.models.operations import LedgerEntry, VideoMetrics
from anime_studio.operations import BatchRunner, FeedbackPolicy, Ledger, load_slate

_FIXTURES = Path(__file__).parent / "fixtures"


def _cfg(tmp_path: Path) -> AnimeStudioConfig:
    cfg = AnimeStudioConfig()
    cfg.llm.provider = "mock"
    cfg.output_dir = str(tmp_path / "output")
    return cfg


def test_load_slate_parses_briefs() -> None:
    briefs = load_slate(_FIXTURES / "slate.yaml")
    assert [b.project_id for b in briefs] == ["slate-sheep", "slate-cat"]
    assert all(isinstance(b, ProjectBrief) for b in briefs)


async def test_batch_runner_produces_and_ledgers(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    briefs = load_slate(_FIXTURES / "slate.yaml")
    entries = await BatchRunner(cfg, concurrency=2).run(briefs)

    assert len(entries) == 2
    assert all(e.status == "completed" for e in entries)
    assert all(e.qa_score is not None for e in entries)

    ledger_path = cfg.output_path / "_ledger.json"
    assert ledger_path.exists()
    rows = json.loads(ledger_path.read_text(encoding="utf-8"))
    assert len(rows) == 2
    summary = Ledger(ledger_path).summary()
    assert summary["total"] == 2 and summary["completed"] == 2


def test_feedback_policy_picks_best_hook() -> None:
    ledger = [
        LedgerEntry(project_id="a", title="A", hook_archetype="paradox", bpm=128, platforms=["tiktok"]),
        LedgerEntry(project_id="b", title="B", hook_archetype="number", bpm=132, platforms=["tiktok"]),
    ]
    metrics = [
        VideoMetrics(project_id="a", platform="tiktok", retention_pct=40, completion_pct=45),
        VideoMetrics(project_id="b", platform="tiktok", retention_pct=80, completion_pct=85),
    ]
    bias = FeedbackPolicy.from_history(metrics, ledger)
    assert bias.preferred_hook == "number"
    assert bias.preferred_bpm == 132
    assert bias.sample_size == 2


def test_feedback_apply_biases_brief() -> None:
    from anime_studio.models.operations import FeedbackBias

    brief = ProjectBrief(
        project_id="x", title_idea="T", logline="l", target_platforms=["youtube_shorts", "tiktok"]
    )
    bias = FeedbackBias(preferred_hook="number", preferred_platform="tiktok", preferred_bpm=132)
    out = FeedbackPolicy.apply(brief, bias)
    assert out.constraints["preferred_hook"] == "number"
    assert out.target_platforms[0] == "tiktok"  # promoted to primary
