"""監督 — Director agent.

Builds the task DAG, runs each department in topological order, applies quality
gates between stages, and requests bounded revisions from the responsible
upstream agent when a gate fails. This mirrors the AniME 'Director Agent統括 +
Specialized Agents' structure: the director makes the creative go/no-go calls,
the departments execute.
"""

from __future__ import annotations

from pydantic import BaseModel

from ..models.edit import EditPlan
from ..models.qa import QAGateResult
from ..models.script import ScriptArtifact
from ..models.storyboard import Storyboard
from ..pipeline.dag import build_dag, topological_sort
from .base import AgentContext, BaseAgent
from .qa import gate_retention, gate_three_second_hook


class PipelineResult(BaseModel):
    artifacts: dict[str, object] = {}
    stage_revisions: dict[str, int] = {}


class DirectorAgent:
    def __init__(self, agents: list[BaseAgent], max_revisions: int = 2, hard_gates: tuple[str, ...] = ()) -> None:
        self._agents = {a.stage_id: a for a in agents}
        self._dag = build_dag(agents)
        self._max_revisions = max_revisions
        self._hard_gates = set(hard_gates)

    @property
    def order(self) -> list[str]:
        return topological_sort(self._dag)

    async def run(self, ctx: AgentContext) -> PipelineResult:
        result = PipelineResult()
        for stage_id in self.order:
            agent = self._agents[stage_id]
            artifact, revisions = await self._run_with_gates(agent, ctx)
            ctx.artifacts[stage_id] = artifact
            ctx.artifacts.pop("_revision_feedback", None)
            result.artifacts[stage_id] = artifact
            result.stage_revisions[stage_id] = revisions
        return result

    async def _run_with_gates(self, agent: BaseAgent, ctx: AgentContext) -> tuple[object, int]:
        artifact: object = None
        for attempt in range(self._max_revisions + 1):
            artifact = await agent.run(ctx)
            gate = self._gate_for(agent.stage_id, artifact, ctx)
            state = "passed" if attempt == 0 else "revised"
            if gate is None or gate.passed:
                await self._emit(ctx, agent, state, gate)
                return artifact, attempt
            # Gate failed: feed the critique back and let the agent retry.
            ctx.artifacts["_revision_feedback"] = gate.feedback
            await self._emit(ctx, agent, "revised", gate)
        # Retries exhausted.
        gate = self._gate_for(agent.stage_id, artifact, ctx)
        if gate is not None and not gate.passed and gate.gate in self._hard_gates:
            raise RuntimeError(f"hard gate '{gate.gate}' failed for stage '{agent.stage_id}': {gate.feedback}")
        await self._emit(ctx, agent, "failed", gate)
        return artifact, self._max_revisions

    def _gate_for(self, stage_id: str, artifact: object, ctx: AgentContext) -> QAGateResult | None:
        if stage_id == "script" and isinstance(artifact, ScriptArtifact):
            return gate_three_second_hook(artifact, ctx.kb)
        if stage_id == "editing" and isinstance(artifact, EditPlan):
            script = ctx.artifacts.get("script")
            storyboard = ctx.artifacts.get("storyboard")
            if isinstance(script, ScriptArtifact) and isinstance(storyboard, Storyboard):
                platform = (ctx.brief.target_platforms or ["youtube_shorts"])[0]
                return gate_retention(script, storyboard, artifact, platform, ctx.kb)
        return None

    async def _emit(self, ctx: AgentContext, agent: BaseAgent, state: str, gate: QAGateResult | None) -> None:
        from ..models.job import ProgressEvent

        await ctx.emit(
            ProgressEvent(
                project_id=ctx.brief.project_id,
                stage_id=agent.stage_id,
                state=state,  # type: ignore[arg-type]
                message=f"{agent.department} ({agent.stage_id})",
                meta={"gate": gate.gate, "passed": gate.passed, "score": gate.score} if gate else {},
            )
        )
