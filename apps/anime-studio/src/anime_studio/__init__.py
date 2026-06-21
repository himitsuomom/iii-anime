"""anime-studio: an AI anime production pipeline run as a studio (会社として回す).

A director agent orchestrates specialized department agents (planning, script,
character design, storyboard, production, editing & sound, QA, distribution)
over a knowledge base of AI-anime production laws, producing a complete
production bible. Built as an iii worker with an engine-independent CLI core.
"""

from .config import AnimeStudioConfig
from .models.brief import ProjectBrief
from .pipeline.orchestrator import PipelineOutput, run_pipeline

__version__ = "0.1.0"

__all__ = ["run_pipeline", "PipelineOutput", "ProjectBrief", "AnimeStudioConfig", "__version__"]
