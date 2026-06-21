from __future__ import annotations

import pytest

from anime_studio.agents.base import AgentContext, BaseAgent
from anime_studio.agents.director import DirectorAgent
from anime_studio.agents.qa import gate_three_second_hook
from anime_studio.models.script import Beat, ScriptArtifact


def _hook_script(end_s: float) -> ScriptArtifact:
    beat = Beat(
        id="hook", label="Hook", start_s=0.0, end_s=end_s, narrative="x", visual_metaphor="y", emotion="surprise"
    )
    return ScriptArtifact(beats=[beat])


class _FlakyScriptAgent(BaseAgent):
    """Fails the 3s-hook gate on the first attempt, fixes it once given feedback."""

    stage_id = "script"
    department = "脚本"
    depends_on = ()
    output_type = ScriptArtifact

    async def run(self, ctx: AgentContext) -> ScriptArtifact:
        return _hook_script(3.0 if ctx.revision_feedback() else 5.0)


class _AlwaysBadScriptAgent(_FlakyScriptAgent):
    async def run(self, ctx: AgentContext) -> ScriptArtifact:
        return _hook_script(9.0)


def _ctx(sample_brief, kb, providers, config) -> AgentContext:
    return AgentContext(brief=sample_brief, kb=kb, providers=providers, config=config, artifacts={})


def test_gate_flags_late_hook(kb) -> None:
    assert gate_three_second_hook(_hook_script(5.0), kb).passed is False


async def test_revision_recovers_within_budget(sample_brief, kb, providers, config) -> None:
    director = DirectorAgent([_FlakyScriptAgent()], max_revisions=2)
    ctx = _ctx(sample_brief, kb, providers, config)
    result = await director.run(ctx)
    script = result.artifacts["script"]
    assert script.beats[0].end_s <= 3.0
    assert result.stage_revisions["script"] >= 1


async def test_hard_gate_aborts_when_unrecoverable(sample_brief, kb, providers, config) -> None:
    director = DirectorAgent([_AlwaysBadScriptAgent()], max_revisions=1, hard_gates=("three_second_hook",))
    ctx = _ctx(sample_brief, kb, providers, config)
    with pytest.raises(RuntimeError, match="hard gate"):
        await director.run(ctx)
