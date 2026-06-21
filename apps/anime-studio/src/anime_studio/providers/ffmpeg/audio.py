"""Procedural audio provider using the bundled ffmpeg (lavfi synthesis).

Not a music model — it synthesises a simple tonal BGM bed and short SE tones so
the animatic has real, beat-aware audio without any external API. Also serves as
the graceful fallback for the hosted audio provider.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from ...models.artifacts import ArtifactDescriptor
from ..types import GenSpec

# A small pentatonic-ish set so different SE cues sound distinct but pleasant.
_SE_FREQS = {"impact": 160.0, "swish": 660.0, "pop": 880.0, "sparkle": 1320.0, "leitmotif": 523.25}


class FfmpegAudioProvider:
    name = "ffmpeg-audio"

    async def generate_bgm(self, spec: GenSpec) -> ArtifactDescriptor:
        duration = float(spec.params.get("duration_s", 30.0))
        bpm = int(spec.params.get("bpm", 128))
        out = _out_path(spec, "bgm.wav")
        # A soft sine bed plus a beat-rate amplitude tremolo to evoke the BPM.
        tremolo_hz = bpm / 60.0
        af = f"vibrato=f=5:d=0.2,tremolo=f={tremolo_hz}:d=0.7,volume=-12dB"
        ok = _try_synth(f"sine=frequency=220:duration={duration:.3f}", af, out)
        return ArtifactDescriptor(
            kind="bgm", status="rendered" if ok else "mock", uri=str(out) if ok else None,
            provider=self.name, prompt=spec.prompt, metadata={"bpm": bpm, "duration_s": duration},
        )

    async def generate_se(self, spec: GenSpec) -> ArtifactDescriptor:
        kind = str(spec.params.get("se_kind", "pop"))
        freq = _SE_FREQS.get(kind, 880.0)
        out = _out_path(spec, f"se_{kind}.wav")
        ok = _try_synth(f"sine=frequency={freq}:duration=0.18", "afade=t=out:st=0.1:d=0.08,volume=-6dB", out)
        return ArtifactDescriptor(
            kind="se", status="rendered" if ok else "mock", uri=str(out) if ok else None,
            provider=self.name, prompt=spec.prompt, metadata={"se_kind": kind},
        )


def _out_path(spec: GenSpec, default: str) -> Path:
    return Path(spec.out_path) if spec.out_path else Path(default)


def _ffmpeg_exe() -> str:
    import imageio_ffmpeg

    return str(imageio_ffmpeg.get_ffmpeg_exe())


def _try_synth(source: str, af: str, out_path: Path) -> bool:
    """Synthesize audio; return False (degrade) if ffmpeg is unavailable/fails."""
    try:
        ffmpeg = _ffmpeg_exe()
    except ImportError:
        return False
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [ffmpeg, "-y", "-f", "lavfi", "-i", source, "-af", af, str(out_path)]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0
