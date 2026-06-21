"""Job tracking + progress emission backed by the iii state worker."""

from __future__ import annotations

from typing import Any, Awaitable, Callable

from ..models.job import PipelineJob, ProgressEvent

JOBS_SCOPE = "anime_studio_jobs"
PROGRESS_SCOPE = "anime_studio_progress"


class JobTracker:
    """Persists job + progress to engine state so `studio::status` can read it."""

    def __init__(self, iii: Any) -> None:
        self._iii = iii

    async def _set(self, scope: str, key: str, value: Any) -> Any:
        return await self._iii.trigger_async(
            {"function_id": "state::set", "payload": {"scope": scope, "key": key, "value": value}}
        )

    async def get_job(self, project_id: str) -> Any | None:
        return await self._iii.trigger_async(
            {"function_id": "state::get", "payload": {"scope": JOBS_SCOPE, "key": project_id}}
        )

    async def save_job(self, job: PipelineJob) -> None:
        await self._set(JOBS_SCOPE, job.project_id, job.model_dump(mode="json"))

    def emitter(self, project_id: str) -> Callable[[ProgressEvent], Awaitable[None]]:
        async def emit(event: ProgressEvent) -> None:
            key = f"{project_id}:{event.stage_id}:{event.state}"
            await self._set(PROGRESS_SCOPE, key, event.model_dump(mode="json"))

        return emit
