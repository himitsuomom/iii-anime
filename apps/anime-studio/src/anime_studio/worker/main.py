"""iii worker entrypoint: registers the studio as a set of engine functions."""

from __future__ import annotations

import os

from iii import InitOptions, register_worker

from ..config import AnimeStudioConfig
from .functions import setup


def main() -> None:
    cfg = AnimeStudioConfig.load()
    engine_ws_url = os.environ.get("III_URL", "ws://localhost:49134")
    iii = register_worker(
        address=engine_ws_url,
        options=InitOptions(
            worker_name="anime-studio",
            otel={"enabled": True, "service_name": "anime-studio"},
        ),
    )
    setup(iii, cfg)
    print("anime-studio worker registered: studio::run_pipeline, render, status, script, storyboard, qa, distribution")


if __name__ == "__main__":
    main()
