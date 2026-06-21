from __future__ import annotations

import pytest

from anime_studio.pipeline.orchestrator import run_pipeline
from anime_studio.render import pil_available

# Skip the whole module when the optional render extra is unavailable.
pytest.importorskip("PIL")
pytest.importorskip("imageio_ffmpeg")


async def test_render_animatic_produces_playable_mp4(sample_brief, config) -> None:
    assert pil_available()
    config.render = True
    output = await run_pipeline(sample_brief, config)

    assert output.animatic_path is not None
    mp4 = output.animatic_path
    assert mp4.exists()
    # A real encoded mp4 is comfortably over a few KB.
    assert mp4.stat().st_size > 2000
    assert mp4.read_bytes()[4:8] == b"ftyp"  # ISO base media file signature

    contactsheet = mp4.parent / "storyboard_contactsheet.png"
    assert contactsheet.exists()
    assert contactsheet.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"


async def test_render_can_be_disabled(sample_brief, config) -> None:
    config.render = False
    output = await run_pipeline(sample_brief, config)
    assert output.animatic_path is None
