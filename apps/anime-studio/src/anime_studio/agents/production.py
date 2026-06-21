"""作画・素材生成部 — Production (per-cut generation prompts, 12 principles)."""

from __future__ import annotations

from ..models.character import CharacterSheet
from ..models.prompts import CutPromptSet, GenerationPrompt
from ..models.storyboard import Cut, Storyboard
from ..providers.types import GenSpec
from .base import AgentContext, BaseAgent

_NEGATIVE = "blurry, extra fingers, inconsistent character, watermark, text artifacts, flicker"


class ProductionAgent(BaseAgent):
    stage_id = "production"
    department = "作画・素材生成"
    depends_on = ("storyboard", "character")
    output_type = CutPromptSet

    async def run(self, ctx: AgentContext) -> CutPromptSet:
        storyboard: Storyboard = self._require(ctx, "storyboard")
        characters: CharacterSheet = self._require(ctx, "character")
        principles = ctx.kb.animation_principles()
        tool = ctx.kb.recommended_video_tool()
        char_desc = characters.characters[0].visual_description if characters.characters else "the character"
        palette = ctx.kb.color_palette("triadic_warm")["prompt"]

        prompts: list[GenerationPrompt] = []
        for cut in storyboard.cuts:
            applied = _principles_for(cut, principles)
            positive = ", ".join(
                [
                    char_desc,
                    *cut.camera.vocab,
                    f"{cut.composition.rule} composition",
                    f"{cut.composition.shot_size} shot",
                    palette,
                    *[v for p in applied for v in p.prompt_vocab[:1]],
                    "silent anime, expressive body language",
                ]
            )
            clip = await ctx.providers.video.generate(
                GenSpec(
                    kind="video",
                    prompt=positive,
                    negative_prompt=_NEGATIVE,
                    params={"duration_s": cut.duration_s, "aspect": "9:16", "recommended_tool": tool},
                )
            )
            prompts.append(
                GenerationPrompt(
                    cut_index=cut.index,
                    positive=positive,
                    negative=_NEGATIVE,
                    animation_principles=[p.id for p in applied],
                    recommended_tool=tool,
                    params={"duration_s": cut.duration_s, "aspect": "9:16"},
                    clip=clip,
                )
            )
        return CutPromptSet(prompts=prompts)


def _principles_for(cut: Cut, principles: list) -> list:  # type: ignore[type-arg]
    # Pick principles whose apply_when matches this cut's role.
    tags = {"camera_move", "character_motion"}
    if cut.beat_id in {"hook", "punchline"}:
        tags |= {"comedic_beat", "emotional_peak", "character_intro"}
    if cut.beat_id == "resolution":
        tags |= {"emotional_peak"}
    chosen = [p for p in principles if set(p.apply_when) & tags]
    return chosen[:3] if chosen else principles[:2]
