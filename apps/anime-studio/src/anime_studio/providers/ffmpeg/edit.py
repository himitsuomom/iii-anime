"""ffmpeg-backed edit provider: concatenate real per-cut clips into one mp4.

This finally exercises the EditProvider seam with real assets. Each clip is
normalised to a common 9:16 frame (scale + pad) so heterogeneous source clips
concatenate cleanly, then joined with the concat demuxer. Uses the ffmpeg binary
bundled by imageio-ffmpeg; degrades (returns a stub) when it or the clips are
unavailable.
"""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from ...models.artifacts import ArtifactDescriptor
from ...models.edit import EditPlan


class FfmpegEditProvider:
    name = "ffmpeg-edit"
    supports_render = True

    def __init__(self, *, width: int = 720, height: int = 1280, fps: int = 24) -> None:
        self._w = width
        self._h = height
        self._fps = fps

    async def assemble(self, edit_plan: EditPlan, clips: list[ArtifactDescriptor]) -> ArtifactDescriptor:
        rendered = [c for c in clips if c.status == "rendered" and c.uri and Path(c.uri).exists()]
        if not rendered:
            return ArtifactDescriptor(
                kind="final_video", status="stub", provider=self.name,
                prompt="no rendered clips to assemble",
            )
        out_path = _output_path(rendered)
        try:
            ffmpeg = _ffmpeg_exe()
        except RuntimeError:
            return ArtifactDescriptor(kind="final_video", status="stub", provider=self.name, prompt="ffmpeg missing")
        self._concat(ffmpeg, [Path(c.uri) for c in rendered], out_path)  # type: ignore[arg-type]
        return ArtifactDescriptor(
            kind="final_video",
            status="rendered",
            uri=str(out_path),
            provider=self.name,
            prompt=f"assembled {len(rendered)} clips at {edit_plan.bpm} BPM",
            metadata={"clips": len(rendered), "bpm": edit_plan.bpm},
        )

    def _concat(self, ffmpeg: str, clips: list[Path], out_path: Path) -> None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        vf = (
            f"scale={self._w}:{self._h}:force_original_aspect_ratio=decrease,"
            f"pad={self._w}:{self._h}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={self._fps},format=yuv420p"
        )
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            normalised: list[Path] = []
            for i, clip in enumerate(clips):
                norm = tmp_dir / f"n_{i:03d}.mp4"
                cmd = [ffmpeg, "-y", "-i", str(clip), "-vf", vf, "-an", str(norm)]
                _run(cmd)
                normalised.append(norm)
            listing = "\n".join(f"file '{p.as_posix()}'" for p in normalised) + "\n"
            concat_file = tmp_dir / "list.txt"
            concat_file.write_text(listing, encoding="utf-8")
            _run([ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", str(concat_file),
                  "-movflags", "+faststart", str(out_path)])


def _output_path(clips: list[ArtifactDescriptor]) -> Path:
    # Place the final mp4 next to the cuts (output/<project>/assets/cuts -> render/).
    first = Path(clips[0].uri)  # type: ignore[arg-type]
    return first.parent.parent.parent / "render" / "final.mp4"


def _ffmpeg_exe() -> str:
    import imageio_ffmpeg

    return str(imageio_ffmpeg.get_ffmpeg_exe())


def _run(cmd: list[str]) -> None:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:  # pragma: no cover - surfaced only on ffmpeg failure
        raise RuntimeError(f"ffmpeg failed: {result.stderr[-400:]}")
