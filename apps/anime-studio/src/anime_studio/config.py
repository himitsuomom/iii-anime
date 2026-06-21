"""Runtime configuration for anime-studio.

Loaded from an ``anime_studio.toml`` file (searched from the cwd upward, then the
packaged default) and overridden by environment variables. The config drives
provider selection, model ids, output location and the director's revision
behaviour, so the same orchestration core can run all-mock in CI or with the
Anthropic LLM in production.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

try:  # Python 3.11+
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - 3.10 fallback
    import tomli as tomllib

_DEFAULT_TOML = Path(__file__).resolve().parent.parent.parent / "anime_studio.toml"


class LLMConfig(BaseModel):
    provider: str = "anthropic"
    model: str = "claude-opus-4-8"
    max_tokens: int = 4096
    temperature: float = 0.7


class ProviderConfig(BaseModel):
    provider: str = "mock"
    # Hosted-API adapter settings (used when provider == "hosted").
    endpoint: str = ""
    model: str = ""
    api_key_env: str = ""
    timeout: float = 120.0
    poll_interval: float = 2.0
    params: dict[str, Any] = Field(default_factory=dict)

    @property
    def api_key(self) -> str | None:
        return os.environ.get(self.api_key_env) if self.api_key_env else None


class AnimeStudioConfig(BaseModel):
    output_dir: str = "./output"
    max_revisions: int = 2
    hard_gates: list[str] = Field(default_factory=lambda: ["three_second_hook"])
    # When true, also render a playable animatic mp4 (needs the 'render' extra).
    render: bool = False
    llm: LLMConfig = Field(default_factory=LLMConfig)
    image: ProviderConfig = Field(default_factory=ProviderConfig)
    video: ProviderConfig = Field(default_factory=ProviderConfig)
    audio: ProviderConfig = Field(default_factory=ProviderConfig)
    edit: ProviderConfig = Field(default_factory=ProviderConfig)
    # Read directly from env, never persisted to disk.
    anthropic_api_key: str | None = None

    @property
    def output_path(self) -> Path:
        return Path(self.output_dir)

    @classmethod
    def load(cls, path: str | Path | None = None) -> "AnimeStudioConfig":
        """Build config from a TOML file (if found) layered with env overrides."""
        data = _load_toml(path)
        general = data.get("general", {})
        merged: dict[str, Any] = {
            "output_dir": general.get("output_dir", "./output"),
            "max_revisions": general.get("max_revisions", 2),
            "hard_gates": general.get("hard_gates", ["three_second_hook"]),
            "render": data.get("render", {}).get("enabled", False),
            "llm": data.get("llm", {}),
            "image": data.get("image", {}),
            "video": data.get("video", {}),
            "audio": data.get("audio", {}),
            "edit": data.get("edit", {}),
        }
        cfg = cls.model_validate(merged)
        return cfg._apply_env()

    def _apply_env(self) -> "AnimeStudioConfig":
        env = os.environ
        if v := env.get("ANIME_STUDIO_OUTPUT_DIR"):
            self.output_dir = v
        if v := env.get("ANIME_STUDIO_MAX_REVISIONS"):
            self.max_revisions = int(v)
        if v := env.get("ANIME_STUDIO_RENDER"):
            self.render = v.lower() in ("1", "true", "yes", "on")
        if v := env.get("ANIME_STUDIO_LLM_PROVIDER"):
            self.llm.provider = v
        if v := env.get("ANIME_STUDIO_LLM_MODEL"):
            self.llm.model = v
        for cap in ("image", "video", "audio", "edit"):
            if v := env.get(f"ANIME_STUDIO_{cap.upper()}_PROVIDER"):
                getattr(self, cap).provider = v
        # API key is only ever sourced from the environment.
        self.anthropic_api_key = env.get("ANTHROPIC_API_KEY")
        return self


def _load_toml(path: str | Path | None) -> dict[str, Any]:
    candidate = _resolve_toml_path(path)
    if candidate is None or not candidate.exists():
        return {}
    with candidate.open("rb") as fh:
        data: dict[str, Any] = tomllib.load(fh)
    return data


def _resolve_toml_path(path: str | Path | None) -> Path | None:
    if path is not None:
        return Path(path)
    # Search upward from cwd for a project-local config, else packaged default.
    cwd = Path.cwd()
    for directory in (cwd, *cwd.parents):
        candidate = directory / "anime_studio.toml"
        if candidate.exists():
            return candidate
    return _DEFAULT_TOML if _DEFAULT_TOML.exists() else None
