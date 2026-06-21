from __future__ import annotations

from anime_studio.knowledge.loader import KnowledgeBase


def test_script_beats_load_and_validate(kb: KnowledgeBase) -> None:
    beats = kb.script_beats()
    assert beats.framework == "save_the_cat_shorts"
    ids = [b.id for b in beats.beats]
    assert ids == ["hook", "problem", "development", "resolution", "punchline"]


def test_platform_gates(kb: KnowledgeBase) -> None:
    assert kb.platform_spec("youtube_shorts").gate.threshold == 65
    assert kb.platform_spec("tiktok").gate.threshold == 70


def test_camera_and_principles(kb: KnowledgeBase) -> None:
    assert kb.camera_move("dolly_zoom").id == "dolly_zoom"
    ids = {p.id for p in kb.animation_principles()}
    assert {"squash_and_stretch", "anticipation", "follow_through"} <= ids


def test_emotion_metaphor_has_default(kb: KnowledgeBase) -> None:
    assert kb.emotion_to_metaphor("joy").visual
    # Unknown emotion degrades gracefully rather than raising.
    assert kb.emotion_to_metaphor("nonexistent").color == "triadic_warm"


def test_hooks_catalog(kb: KnowledgeBase) -> None:
    hooks = kb.hooks()
    assert len(hooks) >= 5
    assert all(h.id and h.name for h in hooks)
