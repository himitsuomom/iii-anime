from __future__ import annotations

import os
from pathlib import Path

import pytest
import yaml

# Force deterministic mock providers for the whole suite.
os.environ["ANIME_STUDIO_LLM_PROVIDER"] = "mock"

from anime_studio.config import AnimeStudioConfig  # noqa: E402
from anime_studio.knowledge.loader import KnowledgeBase  # noqa: E402
from anime_studio.models.brief import ProjectBrief  # noqa: E402
from anime_studio.providers.registry import build_providers  # noqa: E402

_FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def kb() -> KnowledgeBase:
    return KnowledgeBase.default()


@pytest.fixture
def config(tmp_path: Path) -> AnimeStudioConfig:
    cfg = AnimeStudioConfig()
    cfg.llm.provider = "mock"
    cfg.output_dir = str(tmp_path / "output")
    return cfg


@pytest.fixture
def providers(config: AnimeStudioConfig):
    return build_providers(config)


@pytest.fixture
def sample_brief() -> ProjectBrief:
    data = yaml.safe_load((_FIXTURES / "sample_brief.yaml").read_text(encoding="utf-8"))
    return ProjectBrief.model_validate(data)
