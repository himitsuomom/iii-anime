"""Knowledge base: load + validate + cache the YAML 'laws/principles' data.

Each department agent consults this typed knowledge instead of hardcoding craft
strings, so the principles from the reports can be tuned by editing YAML without
touching code. Each file is validated against a pydantic schema on first access
so a malformed edit fails fast.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

_DATA_DIR = Path(__file__).resolve().parent / "data"


# --- schemas ---------------------------------------------------------------


class ScriptBeat(BaseModel):
    id: str
    label: str
    order: int
    target_seconds: list[float]
    purpose: str
    must_include: list[str] = Field(default_factory=list)
    maps_to_stc: list[str] = Field(default_factory=list)


class ScriptBeatsKB(BaseModel):
    framework: str
    description: str = ""
    total_target_seconds: int = 60
    beats: list[ScriptBeat]


class CameraMoveKB(BaseModel):
    id: str
    label: str
    prompt_vocab: list[str] = Field(default_factory=list)
    effect: str = ""


class AnimationPrinciple(BaseModel):
    id: str
    label: str
    prompt_vocab: list[str] = Field(default_factory=list)
    apply_when: list[str] = Field(default_factory=list)


class PlatformGate(BaseModel):
    metric: str
    threshold: float


class PlatformSpec(BaseModel):
    aspect_ratio: str
    duration_seconds: dict[str, int]
    primary_metric: str
    gate: PlatformGate
    title_max_chars: int = 100
    audio: str = ""
    hashtag_strategy: str = ""
    optimization: str = ""


class Hook(BaseModel):
    id: str
    name: str
    template: str = ""
    curiosity_gap_pattern: str = ""
    example: str = ""


class EmotionMetaphor(BaseModel):
    emotion: str
    visual: list[str]
    color: str


# --- loader ----------------------------------------------------------------


class KnowledgeBase:
    def __init__(self, data_dir: Path | None = None) -> None:
        self._dir = data_dir or _DATA_DIR
        self._cache: dict[str, Any] = {}

    @classmethod
    def default(cls) -> "KnowledgeBase":
        return cls(_DATA_DIR)

    def _raw(self, name: str) -> dict[str, Any]:
        if name not in self._cache:
            path = self._dir / f"{name}.yaml"
            with path.open("r", encoding="utf-8") as fh:
                self._cache[name] = yaml.safe_load(fh)
        data: dict[str, Any] = self._cache[name]
        return data

    # typed accessors -------------------------------------------------------

    def script_beats(self) -> ScriptBeatsKB:
        return ScriptBeatsKB.model_validate(self._raw("script_beats"))

    def camera_moves(self) -> list[CameraMoveKB]:
        return [CameraMoveKB.model_validate(m) for m in self._raw("camera_vocab")["moves"]]

    def camera_move(self, move_id: str) -> CameraMoveKB:
        for move in self.camera_moves():
            if move.id == move_id:
                return move
        raise KeyError(f"unknown camera move: {move_id}")

    def animation_principles(self) -> list[AnimationPrinciple]:
        return [AnimationPrinciple.model_validate(p) for p in self._raw("animation_principles")["principles"]]

    def platform_spec(self, platform: str) -> PlatformSpec:
        platforms = self._raw("platform_specs")["platforms"]
        if platform not in platforms:
            raise KeyError(f"unknown platform: {platform}")
        return PlatformSpec.model_validate(platforms[platform])

    def hooks(self) -> list[Hook]:
        return [Hook.model_validate(h) for h in self._raw("hooks_catalog")["hooks"]]

    def emotion_to_metaphor(self, emotion: str) -> EmotionMetaphor:
        emotions = self._raw("emotion_metaphor")["emotions"]
        key = emotion.lower()
        entry = emotions.get(key)
        if entry is None:
            # graceful default keeps the pipeline running for novel emotions.
            return EmotionMetaphor(emotion=key, visual=["expressive body language"], color="triadic_warm")
        return EmotionMetaphor(emotion=key, visual=entry["visual"], color=entry["color"])

    def composition_rules(self) -> list[dict[str, Any]]:
        return list(self._raw("composition")["rules"])

    def shot_sizes(self) -> list[dict[str, Any]]:
        return list(self._raw("composition")["shot_sizes"])

    def editing_tempo(self) -> dict[str, Any]:
        return dict(self._raw("editing_tempo"))

    def audio_design(self) -> dict[str, Any]:
        return dict(self._raw("audio_design"))

    def color_palette(self, name: str) -> dict[str, Any]:
        palettes = self._raw("color_psychology")["palettes"]
        return dict(palettes.get(name, palettes["triadic_warm"]))

    def tooling(self) -> dict[str, Any]:
        return dict(self._raw("tooling_map"))

    def recommended_video_tool(self) -> str:
        return str(self._raw("tooling_map").get("default_recommended_tool", "AniSora"))

    def stepps(self) -> list[dict[str, Any]]:
        return list(self._raw("virality")["stepps"])

    def raw(self, name: str) -> dict[str, Any]:
        """Escape hatch for files without a dedicated accessor."""
        return self._raw(name)


@lru_cache(maxsize=1)
def default_knowledge_base() -> KnowledgeBase:
    return KnowledgeBase.default()
