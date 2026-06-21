"""配信最適化部 — Distribution (platform variants, thumbnail, titles)."""

from __future__ import annotations

from ..models.distribution import DistributionPlan, PlatformVariant, ThumbnailSpec, TitleCandidate
from ..models.script import ScriptArtifact
from ..providers.types import LLMMessage
from .base import AgentContext, BaseAgent


class DistributionAgent(BaseAgent):
    stage_id = "distribution"
    department = "配信最適化"
    depends_on = ("script", "qa")
    output_type = DistributionPlan

    async def run(self, ctx: AgentContext) -> DistributionPlan:
        brief = ctx.brief
        script: ScriptArtifact = self._require(ctx, "script")
        platforms = brief.target_platforms or ["youtube_shorts"]

        variants: list[PlatformVariant] = []
        for platform in platforms:
            spec = ctx.kb.platform_spec(platform)
            variants.append(
                PlatformVariant(
                    platform=platform,
                    duration_s=int(spec.duration_seconds["sweet_spot"]),
                    aspect_ratio=spec.aspect_ratio,
                    audio_strategy=spec.audio,
                    caption=f"{brief.logline} #{platform}",
                    hashtags=_hashtags(platform),
                )
            )

        titles = await self._titles(ctx, script)
        thumb_emotion = script.beats[0].emotion if script.beats else "surprise"
        thumbnail = ThumbnailSpec(
            concept=f"Big {thumb_emotion} expression of the lead, 9:16, high contrast",
            focal_point="character face (1/3-1/2 of frame)",
            emotion=thumb_emotion,
            text_overlay=brief.title_idea[:18],
        )
        return DistributionPlan(variants=variants, thumbnail=thumbnail, titles=titles)

    async def _titles(self, ctx: AgentContext, script: ScriptArtifact) -> list[TitleCandidate]:
        candidates: list[TitleCandidate] = []
        for hook in ctx.kb.hooks()[:3]:
            resp = await ctx.providers.llm.complete(
                [LLMMessage(content=f"Curiosity-gap title ({hook.name}: {hook.template}) for: {script.logline}")],
                system="You write high-CTR short-form titles using the curiosity gap.",
                max_tokens=ctx.config.llm.max_tokens,
                temperature=ctx.config.llm.temperature,
            )
            candidates.append(
                TitleCandidate(
                    text=resp.text,
                    hook_archetype=hook.id,
                    ctr_rationale=hook.curiosity_gap_pattern,
                )
            )
        return candidates


def _hashtags(platform: str) -> list[str]:
    base = ["#anime", "#shorts", "#kidsanime"]
    if platform == "tiktok":
        return ["#anime", "#fyp", "#cartoon"]
    if platform == "instagram_reels":
        return ["#anime", "#reels", "#animation"]
    return base
