"""Studio departments: the director and the specialized agents."""

from .base import AgentContext, BaseAgent
from .character import CharacterDesignAgent
from .director import DirectorAgent, PipelineResult
from .distribution import DistributionAgent
from .editing import EditingAgent
from .planning import PlanningAgent
from .production import ProductionAgent
from .qa import QAAgent
from .script import ScriptAgent
from .storyboard import StoryboardAgent


def default_agents() -> list[BaseAgent]:
    """The full studio roster, in no particular order (director topo-sorts)."""
    return [
        PlanningAgent(),
        ScriptAgent(),
        CharacterDesignAgent(),
        StoryboardAgent(),
        ProductionAgent(),
        EditingAgent(),
        QAAgent(),
        DistributionAgent(),
    ]


__all__ = [
    "AgentContext",
    "BaseAgent",
    "DirectorAgent",
    "PipelineResult",
    "PlanningAgent",
    "ScriptAgent",
    "CharacterDesignAgent",
    "StoryboardAgent",
    "ProductionAgent",
    "EditingAgent",
    "QAAgent",
    "DistributionAgent",
    "default_agents",
]
