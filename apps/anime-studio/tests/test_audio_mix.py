from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from anime_studio.models.edit import AudioCue, EditPlan
from anime_studio.providers.ffmpeg.audio import FfmpegAudioProvider
from anime_studio.providers.types import GenSpec
from anime_studio.render.audio_mix import mux_audio

pytest.importorskip("imageio_ffmpeg")
import imageio_ffmpeg  # noqa: E402

_FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()


def _make_silent_video(path: Path, seconds: float = 1.5) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        _FFMPEG, "-y", "-f", "lavfi", "-i", f"color=c=black:s=320x568:d={seconds}",
        "-pix_fmt", "yuv420p", str(path),
    ]
    subprocess.run(cmd, capture_output=True, check=True)


def _has_audio_stream(path: Path) -> bool:
    out = subprocess.run([_FFMPEG, "-i", str(path)], capture_output=True, text=True)
    return "Audio:" in out.stderr


async def test_ffmpeg_audio_generates_real_assets(tmp_path: Path) -> None:
    provider = FfmpegAudioProvider()
    bgm = await provider.generate_bgm(GenSpec(kind="bgm", prompt="bed", out_path=str(tmp_path / "bgm.wav"),
                                              params={"bpm": 128, "duration_s": 1.5}))
    assert bgm.status == "rendered"
    assert Path(bgm.uri).exists()  # type: ignore[arg-type]


async def test_mux_audio_adds_audio_stream(tmp_path: Path) -> None:
    video = tmp_path / "render" / "animatic.mp4"
    _make_silent_video(video)
    provider = FfmpegAudioProvider()
    bgm = await provider.generate_bgm(GenSpec(kind="bgm", prompt="bed", out_path=str(tmp_path / "assets" / "bgm.wav"),
                                              params={"duration_s": 1.5}))
    se = await provider.generate_se(GenSpec(kind="se", prompt="ding", out_path=str(tmp_path / "assets" / "se.wav"),
                                            params={"se_kind": "leitmotif"}))
    plan = EditPlan(
        bpm=128,
        audio_cues=[AudioCue(at_s=0.0, kind="bgm", description="bed", uri=bgm.uri),
                    AudioCue(at_s=0.5, kind="leitmotif", description="ding", uri=se.uri)],
    )
    out = mux_audio(video, plan, tmp_path / "render" / "animatic_av.mp4")
    assert out is not None
    assert _has_audio_stream(out)


def test_mux_audio_noop_without_assets(tmp_path: Path) -> None:
    plan = EditPlan(audio_cues=[AudioCue(at_s=0.0, kind="bgm", description="x", uri=None)])
    assert mux_audio(tmp_path / "v.mp4", plan, tmp_path / "out.mp4") is None
