"""品質管理部 — QA (AniEval-style quality gates).

The gate functions are pure and importable so the DirectorAgent can run them
inline between stages, and the QAAgent can aggregate them into a report.
"""

from __future__ import annotations

from ..knowledge.loader import KnowledgeBase
from ..models.edit import EditPlan
from ..models.qa import QAGateResult, QAReport
from ..models.script import ScriptArtifact
from ..models.storyboard import Storyboard
from .base import AgentContext, BaseAgent


def gate_three_second_hook(script: ScriptArtifact, kb: KnowledgeBase) -> QAGateResult:
    rule = kb.editing_tempo()["rules"]["three_second_hook"]
    limit = float(rule["max_hook_end_s"])
    hook = next((b for b in script.beats if b.id == "hook"), None)
    if hook is None:
        return QAGateResult(gate="three_second_hook", passed=False, score=0.0, feedback="No hook beat present.")
    passed = hook.end_s <= limit
    return QAGateResult(
        gate="three_second_hook",
        passed=passed,
        score=round(min(limit / max(hook.end_s, 0.01), 1.0), 2),
        feedback="" if passed else f"Hook ends at {hook.end_s}s; compress it to <= {limit}s with an earlier shock.",
    )


def gate_visual_change_cadence(storyboard: Storyboard, kb: KnowledgeBase) -> QAGateResult:
    rule = kb.editing_tempo()["rules"]["visual_change_cadence"]
    limit = float(rule["max_seconds_between_changes"])
    longest = max((c.duration_s for c in storyboard.cuts), default=0.0)
    passed = longest <= limit + 1e-6
    return QAGateResult(
        gate="visual_change_cadence",
        passed=passed,
        score=round(min(limit / max(longest, 0.01), 1.0), 2),
        feedback="" if passed else f"A cut runs {longest}s; split cuts so none exceed {limit}s.",
    )


def gate_loop_structure(edit: EditPlan, kb: KnowledgeBase) -> QAGateResult:
    has_loop = bool(edit.loop_strategy) and any(c.kind == "silence" for c in edit.audio_cues)
    return QAGateResult(
        gate="loop_structure",
        passed=has_loop,
        score=1.0 if has_loop else 0.0,
        feedback="" if has_loop else "Add a loop-back so the last frame connects to the first.",
    )


def gate_retention(
    script: ScriptArtifact, storyboard: Storyboard, edit: EditPlan, platform: str, kb: KnowledgeBase
) -> QAGateResult:
    spec = kb.platform_spec(platform)
    # Heuristic retention proxy from the craft signals we control.
    hook = gate_three_second_hook(script, kb)
    cadence = gate_visual_change_cadence(storyboard, kb)
    loop = gate_loop_structure(edit, kb)
    score_pct = 100.0 * (0.45 * hook.score + 0.35 * cadence.score + 0.20 * loop.score)  # type: ignore[operator]
    threshold = spec.gate.threshold
    passed = score_pct >= threshold
    return QAGateResult(
        gate=f"retention_{platform}",
        passed=passed,
        score=round(score_pct, 1),
        feedback=""
        if passed
        else f"Projected {score_pct:.0f}% vs {threshold:.0f}% gate on {platform}: strengthen hook/cadence/loop.",
    )


class QAAgent(BaseAgent):
    stage_id = "qa"
    department = "品質管理"
    depends_on = ("script", "storyboard", "editing")
    output_type = QAReport

    async def run(self, ctx: AgentContext) -> QAReport:
        script: ScriptArtifact = self._require(ctx, "script")
        storyboard: Storyboard = self._require(ctx, "storyboard")
        edit: EditPlan = self._require(ctx, "editing")
        platforms = ctx.brief.target_platforms or ["youtube_shorts"]

        gates = [
            gate_three_second_hook(script, ctx.kb),
            gate_visual_change_cadence(storyboard, ctx.kb),
            gate_loop_structure(edit, ctx.kb),
            *[gate_retention(script, storyboard, edit, p, ctx.kb) for p in platforms],
        ]
        failed = [g.gate for g in gates if not g.passed]
        return QAReport(gates=gates, passed=not failed, revision_requested_for=failed)
