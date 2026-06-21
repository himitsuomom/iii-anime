"""編集・音響部 — Editing & sound (beat-match, BPM, leitmotif, loop)."""

from __future__ import annotations

from ..models.edit import AudioCue, EditPlan, EditSegment
from ..models.storyboard import Storyboard
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
            if i == 0:
                cues.append(AudioCue(at_s=0.0, kind="leitmotif", description=audio["leitmotif_note"]))
            clock = out

        total = round(clock, 2)
        # Strategic silence right before the punchline, then a loop-back.
        cues.append(AudioCue(at_s=max(total - 1.0, 0.0), kind="silence", description=audio["silence_note"]))
        cues.append(AudioCue(at_s=0.0, kind="bgm", description=f"BPM {bpm} upbeat track, beat-matched cuts"))

        return EditPlan(
            bpm=bpm,
            segments=segments,
            audio_cues=cues,
            leitmotif=audio["leitmotif_note"],
            loop_strategy=tempo["rules"]["loop_structure"]["note"],
        )
