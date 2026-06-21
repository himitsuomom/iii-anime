"""脚本部 — Script department (Save the Cat 5-beat for Shorts)."""

from __future__ import annotations

from ..models.script import Beat, ScriptArtifact
from ..providers.types import LLMMessage
from .base import AgentContext, BaseAgent

# Beat id -> dominant emotion (drives the visual metaphor lookup).
_BEAT_EMOTION = {
    "hook": "surprise",
    "problem": "sadness",
    "development": "fear",
    "resolution": "joy",
    "punchline": "joy",
}


class ScriptAgent(BaseAgent):
    stage_id = "script"
    department = "脚本"
    depends_on = ("planning",)
    output_type = ScriptArtifact

    async def run(self, ctx: AgentContext) -> ScriptArtifact:
        brief = ctx.brief
        kb_beats = ctx.kb.script_beats()
        duration = float(brief.target_duration_s)
        total = float(kb_beats.total_target_seconds) or duration
        scale = duration / total

        feedback = ctx.revision_feedback()
        beats: list[Beat] = []
        for kb_beat in sorted(kb_beats.beats, key=lambda b: b.order):
            start = round(kb_beat.target_seconds[0] * scale, 2)
            end = round(kb_beat.target_seconds[1] * scale, 2)
            # Honour the 3-second hook rule even after scaling.
            if kb_beat.id == "hook":
                end = min(end, 3.0)
            emotion = _BEAT_EMOTION.get(kb_beat.id, "curiosity")
            metaphor = ctx.kb.emotion_to_metaphor(emotion)
            resp = await ctx.providers.llm.complete(
                [
                    LLMMessage(
                        content=(
                            f"Beat '{kb_beat.label}' ({kb_beat.purpose}) for: {brief.logline}. "
                            f"Silent, visual only. {('Revise per: ' + feedback) if feedback else ''}"
                        )
                    )
                ],
                system="You are a scriptwriter for silent children's anime shorts.",
                max_tokens=ctx.config.llm.max_tokens,
                temperature=ctx.config.llm.temperature,
            )
            beats.append(
                Beat(
                    id=kb_beat.id,
                    label=kb_beat.label,
                    start_s=start,
                    end_s=end,
                    narrative=resp.text,
                    visual_metaphor="; ".join(metaphor.visual),
                    emotion=emotion,
                )
            )

        return ScriptArtifact(
            framework=kb_beats.framework,
            logline=brief.logline,
            theme=brief.tone,
            beats=beats,
            silent_storytelling_notes=[
                "No dialogue: convey every beat with a single visual metaphor.",
                "Emotion shown via eye size, shoulder position and gait.",
                ctx.kb.raw("story_frameworks")["frameworks"]["silent_visual"]["note"],
            ],
        )
