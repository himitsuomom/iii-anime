"""Feedback loop: bias the next slate toward what historically performed best."""

from __future__ import annotations

from collections import defaultdict
from typing import TypeVar

from ..models.brief import ProjectBrief
from ..models.operations import FeedbackBias, LedgerEntry, VideoMetrics

_K = TypeVar("_K")


class FeedbackPolicy:
    """Aggregate past metrics by hook / platform / BPM and recommend a bias."""

    @staticmethod
    def from_history(metrics: list[VideoMetrics], ledger: list[LedgerEntry]) -> FeedbackBias:
        by_project = {e.project_id: e for e in ledger}
        hook_scores: dict[str, list[float]] = defaultdict(list)
        platform_scores: dict[str, list[float]] = defaultdict(list)
        bpm_scores: dict[int, list[float]] = defaultdict(list)

        for m in metrics:
            entry = by_project.get(m.project_id)
            score = (m.retention_pct + m.completion_pct) / 2.0
            if entry and entry.hook_archetype:
                hook_scores[entry.hook_archetype].append(score)
            platform_scores[m.platform].append(score)
            if entry and entry.bpm is not None:
                bpm_scores[entry.bpm].append(score)

        return FeedbackBias(
            preferred_hook=_best(hook_scores),
            preferred_platform=_best(platform_scores),
            preferred_bpm=_best(bpm_scores),
            sample_size=len(metrics),
        )

    @staticmethod
    def apply(brief: ProjectBrief, bias: FeedbackBias) -> ProjectBrief:
        """Return a copy of the brief nudged toward the recommended bias."""
        updated = brief.model_copy(deep=True)
        if bias.preferred_hook:
            updated.constraints["preferred_hook"] = bias.preferred_hook
        if bias.preferred_bpm:
            updated.constraints["preferred_bpm"] = bias.preferred_bpm
        if bias.preferred_platform and bias.preferred_platform in updated.target_platforms:
            # Promote the best-performing platform to primary.
            updated.target_platforms.remove(bias.preferred_platform)
            updated.target_platforms.insert(0, bias.preferred_platform)
        return updated


def _best(scores: dict[_K, list[float]]) -> _K | None:
    if not scores:
        return None
    return max(scores.items(), key=lambda kv: sum(kv[1]) / len(kv[1]))[0]
