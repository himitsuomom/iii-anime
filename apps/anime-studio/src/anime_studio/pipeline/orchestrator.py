"""In-process pipeline orchestration shared by the CLI and the iii worker."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..agents import DirectorAgent, default_agents
from ..agents.base import AgentContext, EmitFn, _noop_emit
from ..config import AnimeStudioConfig
from ..knowledge.loader import KnowledgeBase, default_knowledge_base
from ..models.brief import ProjectBrief
from ..providers.registry import ProviderBundle, build_providers
from .bible import render_bible
from .writer import write_artifacts


@dataclass
class PipelineOutput:
    project_id: str
    output_dir: Path
    artifacts: dict[str, Any]
    stage_revisions: dict[str, int]
    bible_path: Path
    files: list[Path] = field(default_factory=list)


async def run_pipeline(
    brief: ProjectBrief,
    config: AnimeStudioConfig | None = None,
    *,
    kb: KnowledgeBase | None = None,
    providers: ProviderBundle | None = None,
    emit: EmitFn = _noop_emit,
) -> PipelineOutput:
    """Run the full studio pipeline and write the production bible to disk."""
    cfg = config or AnimeStudioConfig.load()
    kb = kb or default_knowledge_base()
    providers = providers or build_providers(cfg)

    ctx = AgentContext(brief=brief, kb=kb, providers=providers, config=cfg, artifacts={}, emit=emit)
    director = DirectorAgent(
        default_agents(),
        max_revisions=cfg.max_revisions,
        hard_gates=tuple(cfg.hard_gates),
    )
    result = await director.run(ctx)

    project_dir = cfg.output_path / brief.project_id
    files = write_artifacts(project_dir, brief, result.artifacts)
    bible_path = project_dir / "production_bible.md"
    bible_path.write_text(render_bible(brief, result.artifacts), encoding="utf-8")
    files.append(bible_path)

    return PipelineOutput(
        project_id=brief.project_id,
        output_dir=project_dir,
        artifacts=result.artifacts,
        stage_revisions=result.stage_revisions,
        bible_path=bible_path,
        files=files,
    )


__all__ = ["run_pipeline", "PipelineOutput"]
