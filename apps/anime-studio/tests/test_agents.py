from __future__ import annotations

import pytest

from anime_studio.agents import (
    CharacterDesignAgent,
    EditingAgent,
    PlanningAgent,
    ProductionAgent,
    QAAgent,
    ScriptAgent,
    StoryboardAgent,
)
from anime_studio.agents.base import AgentContext
from anime_studio.models.edit import EditPlan
from anime_studio.models.prompts import CutPromptSet
from anime_studio.models.qa import QAReport
from anime_studio.models.script import CreativeBrief, ScriptArtifact
from anime_studio.models.storyboard import Storyboard


@pytest.fixture
def ctx(sample_brief, kb, providers, config) -> AgentContext:
    return AgentContext(brief=sample_brief, kb=kb, providers=providers, config=config, artifacts={})


async def _seed(ctx: AgentContext) -> AgentContext:
    ctx.artifacts["planning"] = await PlanningAgent().run(ctx)
    ctx.artifacts["script"] = await ScriptAgent().run(ctx)
    ctx.artifacts["character"] = await CharacterDesignAgent().run(ctx)
    ctx.artifacts["storyboard"] = await StoryboardAgent().run(ctx)
    ctx.artifacts["editing"] = await EditingAgent().run(ctx)
    return ctx


async def test_planning_produces_creative_brief(ctx: AgentContext) -> None:
    out = await PlanningAgent().run(ctx)
    assert isinstance(out, CreativeBrief)
    assert out.primary_platform == "youtube_shorts"


async def test_script_has_five_ascending_beats(ctx: AgentContext) -> None:
    ctx.artifacts["planning"] = await PlanningAgent().run(ctx)
    script = await ScriptAgent().run(ctx)
    assert isinstance(script, ScriptArtifact)
    assert [b.id for b in script.beats] == ["hook", "problem", "development", "resolution", "punchline"]
    # Non-overlapping ascending timecodes.
    for prev, nxt in zip(script.beats, script.beats[1:]):
        assert prev.end_s <= nxt.start_s + 1e-6
    # 3-second hook rule honoured.
    assert script.beats[0].end_s <= 3.0


async def test_storyboard_cuts_reference_valid_beats(ctx: AgentContext) -> None:
    await _seed(ctx)
    storyboard: Storyboard = ctx.artifacts["storyboard"]
    beat_ids = {b.id for b in ctx.artifacts["script"].beats}
    assert storyboard.cuts
    assert all(c.beat_id in beat_ids for c in storyboard.cuts)
    # Indices are contiguous from 1.
    assert [c.index for c in storyboard.cuts] == list(range(1, len(storyboard.cuts) + 1))


async def test_production_prompts_cover_every_cut(ctx: AgentContext) -> None:
    await _seed(ctx)
    prompts: CutPromptSet = await ProductionAgent().run(ctx)
    cut_indices = {c.index for c in ctx.artifacts["storyboard"].cuts}
    assert {p.cut_index for p in prompts.prompts} == cut_indices
    assert all(p.positive for p in prompts.prompts)


async def test_editing_plan_has_segments(ctx: AgentContext) -> None:
    await _seed(ctx)
    plan: EditPlan = ctx.artifacts["editing"]
    assert plan.segments
    assert plan.bpm in (120, 128, 132, 140)


async def test_qa_report_aggregates_gates(ctx: AgentContext) -> None:
    await _seed(ctx)
    report: QAReport = await QAAgent().run(ctx)
    assert isinstance(report, QAReport)
    gate_names = {g.gate for g in report.gates}
    assert "three_second_hook" in gate_names
