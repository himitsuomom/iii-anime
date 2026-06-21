"""Task dependency graph + topological ordering for the director."""

from __future__ import annotations

from collections.abc import Iterable, Mapping


def build_dag(agents: Iterable[object]) -> dict[str, tuple[str, ...]]:
    """Map each agent's stage_id to its dependency stage_ids."""
    dag: dict[str, tuple[str, ...]] = {}
    for agent in agents:
        stage_id = getattr(agent, "stage_id")
        dag[stage_id] = tuple(getattr(agent, "depends_on", ()))
    _validate(dag)
    return dag


def _validate(dag: Mapping[str, tuple[str, ...]]) -> None:
    for stage, deps in dag.items():
        for dep in deps:
            if dep not in dag:
                raise ValueError(f"stage '{stage}' depends on unknown stage '{dep}'")


def topological_sort(dag: Mapping[str, tuple[str, ...]]) -> list[str]:
    """Return stages in dependency order; raises on a cycle."""
    visited: dict[str, int] = {}  # 0 = visiting, 1 = done
    order: list[str] = []

    def visit(node: str, stack: tuple[str, ...]) -> None:
        state = visited.get(node)
        if state == 1:
            return
        if state == 0:
            cycle = " -> ".join((*stack, node))
            raise ValueError(f"cycle detected in pipeline DAG: {cycle}")
        visited[node] = 0
        for dep in dag[node]:
            visit(dep, (*stack, node))
        visited[node] = 1
        order.append(node)

    for node in dag:
        visit(node, ())
    return order
