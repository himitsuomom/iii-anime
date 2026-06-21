"""Assemble storyboard frames into a playable animatic mp4 (+ contact sheet).

Uses Pillow to draw frames and the ffmpeg binary bundled by ``imageio-ffmpeg``
(no system install required). Durations come from the edit plan, so the output
is beat-aware. Degrades with a clear ``RenderUnavailable`` when the optional
'render' extra is not installed.
"""

from __future__ import annotations

import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..knowledge.loader import KnowledgeBase
from ..models.brief import ProjectBrief
from ..models.edit import EditPlan
from ..models.storyboard import Storyboard
from .frames import pil_available, render_cut_frame


class RenderUnavailable(RuntimeError):
    """Raised when the optional render dependencies are missing."""


@dataclass
class RenderResult:
    mp4_path: Path
    contactsheet_path: Path
    frame_count: int
    duration_s: float


def _ffmpeg_exe() -> str:
    try:
        import imageio_ffmpeg
    except ImportError as exc:  # pragma: no cover - exercised only without the extra
        raise RenderUnavailable("imageio-ffmpeg is required. Install the 'render' extra.") from exc
    return str(imageio_ffmpeg.get_ffmpeg_exe())


def _durations(storyboard: Storyboard, edit: EditPlan | None) -> dict[int, float]:
    if edit and edit.segments:
        return {seg.cut_index: max(seg.out_s - seg.in_s, 0.4) for seg in edit.segments}
    return {cut.index: max(cut.duration_s, 0.4) for cut in storyboard.cuts}


def render_animatic(
    brief: ProjectBrief,
    artifacts: dict[str, Any],
    out_dir: Path,
    kb: KnowledgeBase,
    *,
    fps: int = 24,
    width: int = 720,
    height: int = 1280,
) -> RenderResult:
    """Render the storyboard into an animatic mp4 and a storyboard contact sheet."""
    if not pil_available():
        raise RenderUnavailable("Pillow is required. Install the 'render' extra (pip install 'anime-studio[render]').")

    storyboard = artifacts.get("storyboard")
    if not isinstance(storyboard, Storyboard) or not storyboard.cuts:
        raise RenderUnavailable("No storyboard cuts to render.")
    edit = artifacts.get("editing") if isinstance(artifacts.get("editing"), EditPlan) else None

    from PIL import Image

    out_dir.mkdir(parents=True, exist_ok=True)
    durations = _durations(storyboard, edit)

    frames: list[Image.Image] = [
        render_cut_frame(cut, kb, width=width, height=height, title=brief.title_idea) for cut in storyboard.cuts
    ]

    mp4_path = out_dir / "animatic.mp4"
    total = _encode_mp4(frames, storyboard, durations, mp4_path, fps=fps, ffmpeg=_ffmpeg_exe())
    contactsheet_path = out_dir / "storyboard_contactsheet.png"
    _contact_sheet(frames, contactsheet_path)

    return RenderResult(
        mp4_path=mp4_path,
        contactsheet_path=contactsheet_path,
        frame_count=len(frames),
        duration_s=round(total, 2),
    )


def _encode_mp4(
    frames: list[Any],
    storyboard: Storyboard,
    durations: dict[int, float],
    mp4_path: Path,
    *,
    fps: int,
    ffmpeg: str,
) -> float:
    """Write frames to a temp dir and concat them with per-cut durations."""
    total = 0.0
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        listing: list[str] = []
        for cut, frame in zip(storyboard.cuts, frames):
            frame_path = tmp_dir / f"cut_{cut.index:03d}.png"
            frame.save(frame_path)
            dur = durations.get(cut.index, cut.duration_s)
            total += dur
            listing.append(f"file '{frame_path.as_posix()}'")
            listing.append(f"duration {dur:.3f}")
        # The concat demuxer needs the final frame repeated to honour its duration.
        last_path = tmp_dir / f"cut_{storyboard.cuts[-1].index:03d}.png"
        listing.append(f"file '{last_path.as_posix()}'")

        concat_file = tmp_dir / "frames.txt"
        concat_file.write_text("\n".join(listing) + "\n", encoding="utf-8")

        # The concat demuxer feeds per-image durations; the fps filter resamples
        # that into a constant-frame-rate, widely-playable yuv420p mp4.
        cmd = [
            ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", str(concat_file),
            "-vf", f"fps={fps},format=yuv420p", "-movflags", "+faststart", str(mp4_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:  # pragma: no cover - surfaced only on ffmpeg failure
            raise RenderUnavailable(f"ffmpeg failed: {result.stderr[-500:]}")
    return total


def _contact_sheet(frames: list[Any], path: Path, *, columns: int = 4, thumb_w: int = 240) -> None:
    from PIL import Image

    if not frames:
        return
    ratio = frames[0].height / frames[0].width
    thumb_h = int(thumb_w * ratio)
    rows = (len(frames) + columns - 1) // columns
    sheet = Image.new("RGB", (columns * thumb_w, rows * thumb_h), (16, 16, 20))
    for i, frame in enumerate(frames):
        thumb = frame.resize((thumb_w, thumb_h))
        sheet.paste(thumb, ((i % columns) * thumb_w, (i // columns) * thumb_h))
    sheet.save(path)
