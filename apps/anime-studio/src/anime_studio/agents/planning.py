"""企画部 — Planning department (STEPPS / viral strategy)."""

from __future__ import annotations

from ..models.script import CreativeBrief
from ..providers.types import LLMMessage
from .base import AgentContext, BaseAgent


class PlanningAgent(BaseAgent):
    stage_id = "planning"
    department = "企画"
    depends_on = ()
    output_type = CreativeBrief

    async def run(self, ctx: AgentContext) -> CreativeBrief:
        brief = ctx.brief
        hooks = ctx.kb.hooks()
        stepps = ctx.kb.stepps()
        primary = brief.target_platforms[0] if brief.target_platforms else "youtube_shorts"
        # Honour a feedback-loop bias when present, else default to the top hook.
        preferred = brief.constraints.get("preferred_hook")
        valid_hooks = {h.id for h in hooks}
        hook = preferred if preferred in valid_hooks else (hooks[0].id if hooks else "emotional")
        # Emotion + Stories are the strongest STEPPS levers for kids' anime.
        levers = [s["id"] for s in stepps if s["id"] in {"emotion", "stories", "social_currency"}]

        resp = await ctx.providers.llm.complete(
            [LLMMessage(content=f"One-sentence viral concept for a silent kids' anime short: {brief.logline}")],
            system="You are the planning lead of an anime studio applying the STEPPS virality framework.",
            max_tokens=ctx.config.llm.max_tokens,
            temperature=ctx.config.llm.temperature,
        )
        return CreativeBrief(
            concept=resp.text,
            primary_platform=primary,
            emotional_core=brief.tone,
            hook_archetype=hook,
            stepps_levers=levers or ["emotion", "stories"],
            share_trigger="cute + surprising + heartwarming moment worth tagging a friend",
        )
