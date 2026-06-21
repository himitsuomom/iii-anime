"""Command-line entrypoint: run the studio pipeline without the iii engine."""

from __future__ import annotations

import argparse
import asyncio
import sys
import time
import uuid
from pathlib import Path
from typing import Any

import yaml

from .config import AnimeStudioConfig
from .knowledge.loader import default_knowledge_base
from .logging import default_logger
from .models.brief import ProjectBrief
from .models.job import ProgressEvent
from .pipeline.orchestrator import run_pipeline


def _load_brief(path: Path) -> ProjectBrief:
    data: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    data.setdefault("project_id", f"proj-{int(time.time())}-{uuid.uuid4().hex[:6]}")
    return ProjectBrief.model_validate(data)


def _cmd_run(args: argparse.Namespace) -> int:
    log = default_logger()
    cfg = AnimeStudioConfig.load(args.config)
    if args.output_dir:
        cfg.output_dir = args.output_dir
    if args.provider:
        cfg.llm.provider = args.provider
    if args.render:
        cfg.render = True
    brief = _load_brief(Path(args.brief))

    async def emit(event: ProgressEvent) -> None:
        log.info(f"[{event.state}] {event.message}", event.meta or None)

    output = asyncio.run(run_pipeline(brief, cfg, emit=emit))
    log.info("pipeline complete", {"project_id": output.project_id, "files": len(output.files)})
    print(f"\nProduction bible: {output.bible_path}")
    print(f"Output dir:       {output.output_dir}")
    print(f"Revisions:        {output.stage_revisions}")
    if cfg.render:
        if output.animatic_path is not None:
            print(f"Animatic mp4:     {output.animatic_path}")
        else:
            print("Animatic mp4:     skipped (install the 'render' extra: uv sync --extra render)")
    return 0


def _cmd_validate(args: argparse.Namespace) -> int:
    kb = default_knowledge_base()
    # Touch every typed accessor so a malformed YAML surfaces immediately.
    kb.script_beats()
    kb.camera_moves()
    kb.animation_principles()
    kb.hooks()
    for platform in ("youtube_shorts", "tiktok", "instagram_reels"):
        kb.platform_spec(platform)
    print("knowledge base OK")
    return 0


def _cmd_info(args: argparse.Namespace) -> int:
    from .agents import default_agents

    print("anime-studio departments (topological order resolved by the director):")
    for agent in default_agents():
        deps = ", ".join(agent.depends_on) or "-"
        print(f"  {agent.stage_id:14s} {agent.department:8s} depends_on: {deps}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="anime-studio",
        description="AI anime production pipeline (studio-as-a-company)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="Run the full pipeline from a brief")
    run.add_argument("--brief", required=True, help="Path to a brief YAML file")
    run.add_argument("--output-dir", help="Override output directory")
    run.add_argument("--config", help="Path to anime_studio.toml")
    run.add_argument("--provider", help="Override LLM provider (anthropic|mock)")
    run.add_argument("--render", action="store_true", help="Also render a playable animatic mp4")
    run.set_defaults(func=_cmd_run)

    validate = sub.add_parser("validate", help="Validate the knowledge base")
    validate.set_defaults(func=_cmd_validate)

    info = sub.add_parser("info", help="List the studio departments")
    info.set_defaults(func=_cmd_info)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
