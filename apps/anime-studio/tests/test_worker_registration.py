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
        "studio::batch",
        "studio::enqueue",
        "studio::record_metrics",
        "studio::scheduled_batch",
    }
    assert expected <= set(iii.functions)

    trigger_types = {t["type"] for t in iii.triggers}
    assert "http" in trigger_types
    assert "cron" in trigger_types  # scheduled_batch

    http_paths = {t["config"].get("api_path") for t in iii.triggers if t["type"] == "http"}
    assert {"studio/run", "studio/batch", "studio/enqueue", "studio/metrics"} <= http_paths
    cron = next(t for t in iii.triggers if t["type"] == "cron")
    assert cron["function_id"] == "studio::scheduled_batch"
