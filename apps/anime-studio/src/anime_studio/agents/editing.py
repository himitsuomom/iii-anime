"""編集・音響部 — Editing & sound (beat-match, BPM, leitmotif, loop)."""

from __future__ import annotations

from ..models.edit import AudioCue, EditPlan, EditSegment
from ..models.storyboard import Storyboard
from ..providers.types import GenSpec
from .base import AgentContext, BaseAgent


class EditingAgent(BaseAgent):
    stage_id = "editing"
    department = "編集・音響"
    depends_on = ("storyboard",)
    output_type = EditPlan

    async def run(self, ctx: AgentContext) -> EditPlan:
        storyboard: Storyboard = self._require(ctx, "storyboard")
        audio = ctx.kb.audio_design()
        tempo = ctx.kb.editing_tempo()
        bpm = int(tempo["beat_match"]["recommended_bpm"][1])  # 128 default

        segments: list[EditSegment] = []
        cues: list[AudioCue] = []
        clock = 0.0
        for i, cut in enumerate(storyboard.cuts):
            out = round(clock + cut.duration_s, 2)
            transition = "cut" if i % 4 != 3 else "swish"  # jet-cut rhythm
            segments.append(EditSegment(cut_index=cut.index, in_s=round(clock, 2), out_s=out, transition=transition))
            clock = out

        total = round(clock, 2)
        audio_dir = ctx.asset_dir("audio")

        # Leitmotif SE on the lead's entrance (real asset when an audio provider is set).
        leitmotif_se = await ctx.providers.audio.generate_se(
            GenSpec(
                kind="se",
                prompt=audio["leitmotif_note"],
                out_path=str(audio_dir / "se_leitmotif.wav"),
                params={"se_kind": "leitmotif"},
            )
        )
        cues.append(AudioCue(at_s=0.0, kind="leitmotif", description=audio["leitmotif_note"], uri=leitmotif_se.uri))

        # Strategic silence right before the punchline.
        cues.append(AudioCue(at_s=max(total - 1.0, 0.0), kind="silence", description=audio["silence_note"]))

        # Beat-matched BGM bed for the whole piece.
        bgm = await ctx.providers.audio.generate_bgm(
            GenSpec(
                kind="bgm",
                prompt=f"BPM {bpm} upbeat children's anime track, beat-matched cuts",
                out_path=str(audio_dir / "bgm.wav"),
                params={"bpm": bpm, "duration_s": total},
            )
        )
        cues.append(AudioCue(at_s=0.0, kind="bgm", description=bgm.prompt, uri=bgm.uri))

        return EditPlan(
            bpm=bpm,
            segments=segments,
            audio_cues=cues,
            leitmotif=audio["leitmotif_note"],
            loop_strategy=tempo["rules"]["loop_structure"]["note"],
        )
