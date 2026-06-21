"""Register the studio::* functions and their HTTP triggers on an iii client."""

from __future__ import annotations

import time
import uuid
from typing import Any

from ..agents import default_agents
from ..agents.base import AgentContext
from ..agents.director import DirectorAgent
from ..config import AnimeStudioConfig
from ..knowledge.loader import default_knowledge_base
from ..models.brief import ProjectBrief
from ..models.job import PipelineJob, StageStatus
from ..pipeline.orchestrator import run_pipeline
from ..providers.registry import build_providers
from .progress import JobTracker


def _new_project_id() -> str:
    return f"proj-{int(time.time())}-{uuid.uuid4().hex[:6]}"


def setup(iii: Any, cfg: AnimeStudioConfig | None = None) -> None:
    """Wire every studio function + HTTP trigger onto the iii client."""
    config = cfg or AnimeStudioConfig.load()
    tracker = JobTracker(iii)

    def register(function_id: str, api_path: str, method: str, handler: Any, description: str) -> None:
        iii.register_function(function_id, handler)
        iii.register_trigger(
            {
                "type": "http",
                "function_id": function_id,
                "config": {"api_path": api_path, "http_method": method, "description": description},
            }
        )

    async def run_pipeline_fn(data: dict[str, Any]) -> dict[str, Any]:
        body = (data or {}).get("body") or data or {}
        body.setdefault("project_id", _new_project_id())
        brief = ProjectBrief.model_validate(body)
        job = PipelineJob(project_id=brief.project_id, status="running", output_dir=str(config.output_path))
        await tracker.save_job(job)
        try:
            output = await run_pipeline(brief, config, emit=tracker.emitter(brief.project_id))
            job.status = "completed"
            job.stages = [
                StageStatus(stage_id=s, department=s, state="passed", revisions=r)
                for s, r in output.stage_revisions.items()
            ]
            await tracker.save_job(job)
            return {"statusCode": 201, "body": {"project_id": brief.project_id, "bible": str(output.bible_path)}}
        except Exception as exc:  # noqa: BLE001 - surface failure to the caller + state
            job.status = "failed"
            job.error = str(exc)
            await tracker.save_job(job)
            return {"statusCode": 500, "body": {"project_id": brief.project_id, "error": str(exc)}}

    async def render_fn(data: dict[str, Any]) -> dict[str, Any]:
        body = (data or {}).get("body") or data or {}
        body.setdefault("project_id", _new_project_id())
        brief = ProjectBrief.model_validate(body)
        render_cfg = config.model_copy(update={"render": True})
        output = await run_pipeline(brief, render_cfg, emit=tracker.emitter(brief.project_id))
        if output.animatic_path is None:
            return {"statusCode": 501, "body": {"error": "render extra not installed", "project_id": brief.project_id}}
        return {"statusCode": 201, "body": {"project_id": brief.project_id, "animatic": str(output.animatic_path)}}

    async def status_fn(data: dict[str, Any]) -> dict[str, Any]:
        path_params = (data or {}).get("pathParams") or (data or {}).get("path_params") or {}
        project_id = path_params.get("project_id")
        job = await tracker.get_job(project_id) if project_id else None
        if job is None:
            return {"statusCode": 404, "body": {"error": "job not found", "project_id": project_id}}
        return {"statusCode": 200, "body": job}

    async def stage_fn(data: dict[str, Any], stage_id: str) -> dict[str, Any]:
        """Run a single department (and its upstreams) and return its artifact."""
        body = (data or {}).get("body") or data or {}
        body.setdefault("project_id", _new_project_id())
        brief = ProjectBrief.model_validate(body)
        kb = default_knowledge_base()
        providers = build_providers(config)
        ctx = AgentContext(brief=brief, kb=kb, providers=providers, config=config, artifacts={})
        agents = {a.stage_id: a for a in default_agents()}
        director = DirectorAgent(list(agents.values()), max_revisions=config.max_revisions)
        for sid in director.order:
            artifact = await agents[sid].run(ctx)
            ctx.artifacts[sid] = artifact
            if sid == stage_id:
                return {"statusCode": 200, "body": artifact.model_dump(mode="json")}
        return {"statusCode": 404, "body": {"error": f"unknown stage {stage_id}"}}

    register("studio::run_pipeline", "studio/run", "POST", run_pipeline_fn, "Run the full anime pipeline")
    register("studio::render", "studio/render", "POST", render_fn, "Run the pipeline and render an animatic mp4")
    register("studio::status", "studio/status/:project_id", "GET", status_fn, "Get pipeline job status")
    register(
        "studio::script", "studio/script", "POST", lambda d: stage_fn(d, "script"), "Run the script department"
    )
    register(
        "studio::storyboard",
        "studio/storyboard",
        "POST",
        lambda d: stage_fn(d, "storyboard"),
        "Run through the storyboard department",
    )
    register("studio::qa", "studio/qa", "POST", lambda d: stage_fn(d, "qa"), "Run through QA gates")
    register(
        "studio::distribution",
        "studio/distribution",
        "POST",
        lambda d: stage_fn(d, "distribution"),
        "Run through the distribution department",
    )
