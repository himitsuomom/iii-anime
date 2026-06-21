"""Mix the edit plan's audio cues into a video and mux the result.

Applies the volume-balance discipline from audio_design.yaml (BGM quieter, SE
louder) and offsets each cue by its timeline position with ``adelay``. Uses the
bundled ffmpeg; returns None (caller keeps the silent video) when there's nothing
to mix or ffmpeg is unavailable.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from ..models.edit import EditPlan

# Volume per cue kind (dB), per audio_design.yaml volume balance.
_VOLUME_DB = {"bgm": "-12dB", "se": "-6dB", "leitmotif": "-6dB"}


def _ffmpeg_exe() -> str | None:
    try:
        import imageio_ffmpeg

        return str(imageio_ffmpeg.get_ffmpeg_exe())
    except ImportError:  # pragma: no cover - only without the render extra
        return None


def mux_audio(video_path: Path, edit_plan: EditPlan, out_path: Path) -> Path | None:
    """Mux generated audio cues onto ``video_path`` -> ``out_path``. None if no-op."""
    assets = [c for c in edit_plan.audio_cues if c.uri and Path(c.uri).exists()]
    if not assets:
        return None
    ffmpeg = _ffmpeg_exe()
    if ffmpeg is None or not video_path.exists():
        return None

    inputs: list[str] = ["-i", str(video_path)]
    filters: list[str] = []
    labels: list[str] = []
    for idx, cue in enumerate(assets, start=1):
        inputs += ["-i", str(cue.uri)]
        delay_ms = max(int(cue.at_s * 1000), 0)
        vol = _VOLUME_DB.get(cue.kind, "-9dB")
        filters.append(f"[{idx}:a]adelay=delays={delay_ms}:all=1,volume={vol}[a{idx}]")
        labels.append(f"[a{idx}]")

    if len(labels) == 1:
        filtergraph = filters[0]
        audio_out = labels[0]
    else:
        mix = "".join(labels) + f"amix=inputs={len(labels)}:duration=longest:normalize=0[aout]"
        filtergraph = ";".join(filters) + ";" + mix
        audio_out = "[aout]"

    out_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        ffmpeg, "-y", *inputs, "-filter_complex", filtergraph,
        "-map", "0:v", "-map", audio_out, "-c:v", "copy", "-c:a", "aac", "-shortest", str(out_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:  # pragma: no cover - surfaced only on ffmpeg failure
        return None
    return out_path
