from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from anime_studio.models.artifacts import ArtifactDescriptor
from anime_studio.models.edit import EditPlan
from anime_studio.providers.ffmpeg.edit import FfmpegEditProvider

pytest.importorskip("imageio_ffmpeg")
import imageio_ffmpeg  # noqa: E402


def _make_clip(path: Path, color: str, seconds: float = 0.4) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    cmd = [
        ffmpeg, "-y", "-f", "lavfi", "-i", f"color=c={color}:s=320x568:d={seconds}",
        "-pix_fmt", "yuv420p", str(path),
    ]
    subprocess.run(cmd, capture_output=True, check=True)


async def test_ffmpeg_edit_concatenates_real_clips(tmp_path: Path) -> None:
    cuts = tmp_path / "assets" / "cuts"
    clips = []
    for i, color in enumerate(("red", "green", "blue"), start=1):
        clip_path = cuts / f"cut_{i:02d}.mp4"
        _make_clip(clip_path, color)
        clips.append(ArtifactDescriptor(kind="video", status="rendered", uri=str(clip_path), provider="test"))

    result = await FfmpegEditProvider().assemble(EditPlan(bpm=128), clips)

    assert result.status == "rendered"
    assert result.uri is not None
    final = Path(result.uri)
    assert final.exists()
    assert final.read_bytes()[4:8] == b"ftyp"


async def test_ffmpeg_edit_stub_without_clips() -> None:
    result = await FfmpegEditProvider().assemble(EditPlan(), [])
    assert result.status == "stub"
