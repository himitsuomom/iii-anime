"""絵コンテ部 — Storyboard (composition, camera vocabulary, shot sizes)."""

from __future__ import annotations

import math

from ..models.script import ScriptArtifact
from ..models.storyboard import CameraMove, Composition, Cut, Storyboard
from .base import AgentContext, BaseAgent

# Emotion -> a camera move id that best serves it.
_EMOTION_CAMERA = {
    "surprise": "dolly_zoom",
    "sadness": "static",
    "fear": "tilt",
    "joy": "arc",
    "curiosity": "rack_focus",
}
# Cycle of shot sizes to keep the cadence visually varied.
_SHOT_CYCLE = ["ECU", "WS", "CU", "MS", "FS"]


class StoryboardAgent(BaseAgent):
    stage_id = "storyboard"
    department = "絵コンテ"
    depends_on = ("script",)
    output_type = Storyboard

    async def run(self, ctx: AgentContext) -> Storyboard:
        script: ScriptArtifact = self._require(ctx, "script")
        tempo = ctx.kb.editing_tempo()
        cadence = float(tempo["rules"]["visual_change_cadence"]["max_seconds_between_changes"])
        comp_rules = ctx.kb.composition_rules()

        cuts: list[Cut] = []
        index = 1
        for beat in script.beats:
            beat_len = max(beat.end_s - beat.start_s, 0.1)
            n_cuts = max(1, math.ceil(beat_len / cadence))
            cut_len = round(beat_len / n_cuts, 2)
            metaphor = ctx.kb.emotion_to_metaphor(beat.emotion)
            move_id = _EMOTION_CAMERA.get(beat.emotion, "static")
            move = ctx.kb.camera_move(move_id)
            for j in range(n_cuts):
                shot = _SHOT_CYCLE[(index - 1) % len(_SHOT_CYCLE)]
                rule = comp_rules[(index - 1) % len(comp_rules)]
                cuts.append(
                    Cut(
                        index=index,
                        beat_id=beat.id,
                        duration_s=cut_len,
                        description=f"{beat.label} cut {j + 1}: {metaphor.visual[j % len(metaphor.visual)]}",
                        composition=Composition(rule=rule["id"], shot_size=shot, notes=rule["label"]),
                        camera=CameraMove(move_id=move.id, vocab=move.prompt_vocab, effect=move.effect),
                        color_mood=metaphor.color,
                        lighting=_lighting_for(beat.emotion),
                    )
                )
                index += 1
        return Storyboard(cuts=cuts)


def _lighting_for(emotion: str) -> str:
    return {
        "joy": "soft_light",
        "sadness": "soft_light",
        "fear": "top_light",
        "surprise": "hard_light",
        "curiosity": "back_light",
    }.get(emotion, "soft_light")
