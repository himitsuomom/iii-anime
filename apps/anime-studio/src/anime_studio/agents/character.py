"""設定・キャラデザ部 — Character design (staging, color, LoRA consistency)."""

from __future__ import annotations

from ..models.character import CharacterDesign, CharacterSheet
from ..providers.types import GenSpec, LLMMessage
from .base import AgentContext, BaseAgent


class CharacterDesignAgent(BaseAgent):
    stage_id = "character"
    department = "設定・キャラデザ"
    depends_on = ("script",)
    output_type = CharacterSheet

    async def run(self, ctx: AgentContext) -> CharacterSheet:
        brief = ctx.brief
        palette = ctx.kb.color_palette("triadic_warm")
        tooling = ctx.kb.tooling()
        consistency = tooling["consistency"]["note"]

        resp = await ctx.providers.llm.complete(
            [LLMMessage(content=f"Describe the lead character for a silent kids' anime short: {brief.logline}")],
            system="You are a character designer. Keep silhouettes readable and appealing.",
            max_tokens=ctx.config.llm.max_tokens,
            temperature=ctx.config.llm.temperature,
        )
        visual = resp.text
        name = brief.title_idea.split()[0] if brief.title_idea else "Hero"

        # Generate (or mock) a reference image — also serves as a LoRA/init input.
        art = await ctx.providers.image.generate(
            GenSpec(
                kind="image",
                prompt=f"{visual}, {palette['prompt']}, rule of thirds, clear staging",
                out_path=str(ctx.asset_dir("characters") / f"{_slug(name)}.png"),
                params={"aspect": "1:1", "purpose": "lora_reference"},
            )
        )
        protagonist = CharacterDesign(
            name=name,
            role="protagonist",
            visual_description=visual,
            palette=list(palette.get("colors", [])),
            consistency_notes=consistency,
            reference_art=[art],
        )
        return CharacterSheet(characters=[protagonist])


def _slug(name: str) -> str:
    safe = "".join(c if c.isalnum() else "_" for c in name).strip("_")
    return safe or "character"
