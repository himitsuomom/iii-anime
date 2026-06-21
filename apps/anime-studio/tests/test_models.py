from __future__ import annotations

from anime_studio.models import (
    Beat,
    CharacterSheet,
    DistributionPlan,
    EditPlan,
    ScriptArtifact,
    Storyboard,
)


def test_artifacts_round_trip() -> None:
    hook = Beat(id="hook", label="H", start_s=0, end_s=3, narrative="n", visual_metaphor="m", emotion="joy")
    for model in (
        ScriptArtifact(beats=[hook]),
        CharacterSheet(),
        Storyboard(),
        EditPlan(),
        DistributionPlan(),
    ):
        restored = type(model).model_validate(model.model_dump(mode="json"))
        assert restored == model
