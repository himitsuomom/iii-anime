"""Agent base contract and shared context.

Each department agent receives the brief, the knowledge base, the provider
bundle and all upstream artifacts, and returns one typed artifact. Agents are
async to match the iii SDK handler model and to allow real provider calls.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Awaitable, Callable, ClassVar

from pydantic import BaseModel, ConfigDict

from ..config import AnimeStudioConfig
from ..knowledge.loader import KnowledgeBase
from ..models.job import ProgressEvent
from ..providers.registry import ProviderBundle

EmitFn = Callable[[ProgressEvent], Awaitable[None]]


async def _noop_emit(_: ProgressEvent) -> None:
    return None


class AgentContext(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    brief: Any  # ProjectBrief
    kb: KnowledgeBase
    providers: ProviderBundle
    config: AnimeStudioConfig
    artifacts: dict[str, Any] = {}
    emit: EmitFn = _noop_emit

    def revision_feedback(self) -> str:
        """Feedback injected by the director when a quality gate fails."""
        return str(self.artifacts.get("_revision_feedback", ""))


class BaseAgent(ABC):
    stage_id: ClassVar[str]
    department: ClassVar[str]
    depends_on: ClassVar[tuple[str, ...]] = ()
    output_type: ClassVar[type[BaseModel]]

    @abstractmethod
    async def run(self, ctx: AgentContext) -> BaseModel: ...

    def _require(self, ctx: AgentContext, stage_id: str) -> Any:
        if stage_id not in ctx.artifacts:
            raise KeyError(f"{self.stage_id} requires upstream artifact '{stage_id}'")
        return ctx.artifacts[stage_id]
