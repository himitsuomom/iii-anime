from __future__ import annotations

import pytest

from anime_studio.agents import default_agents
from anime_studio.pipeline.dag import build_dag, topological_sort


def test_topological_order_respects_dependencies() -> None:
    dag = build_dag(default_agents())
    order = topological_sort(dag)
    position = {stage: i for i, stage in enumerate(order)}
    for stage, deps in dag.items():
        for dep in deps:
            assert position[dep] < position[stage]


def test_unknown_dependency_raises() -> None:
    with pytest.raises(ValueError):
        build_dag([_FakeAgent("a", ("missing",))])


def test_cycle_detected() -> None:
    dag = {"a": ("b",), "b": ("a",)}
    with pytest.raises(ValueError, match="cycle"):
        topological_sort(dag)


class _FakeAgent:
    def __init__(self, stage_id: str, depends_on: tuple[str, ...]) -> None:
        self.stage_id = stage_id
        self.depends_on = depends_on
