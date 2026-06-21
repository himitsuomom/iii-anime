from __future__ import annotations

from typing import Any

from anime_studio.config import AnimeStudioConfig
from anime_studio.worker.functions import setup


class _FakeIII:
    def __init__(self) -> None:
        self.functions: dict[str, Any] = {}
        self.triggers: list[dict[str, Any]] = []

    def register_function(self, function_id: str, handler: Any) -> Any:
        self.functions[function_id] = handler
        return handler

    def register_trigger(self, trigger: dict[str, Any]) -> Any:
        self.triggers.append(trigger)
        return trigger

    async def trigger_async(self, _: dict[str, Any]) -> Any:
        return None


def test_setup_registers_all_studio_functions() -> None:
    iii = _FakeIII()
    setup(iii, AnimeStudioConfig())

    expected = {
        "studio::run_pipeline",
        "studio::render",
        "studio::status",
        "studio::script",
        "studio::storyboard",
        "studio::qa",
        "studio::distribution",
    }
    assert expected <= set(iii.functions)

    http_paths = {t["config"]["api_path"] for t in iii.triggers}
    assert "studio/run" in http_paths
    assert "studio/status/:project_id" in http_paths
    assert all(t["type"] == "http" for t in iii.triggers)
