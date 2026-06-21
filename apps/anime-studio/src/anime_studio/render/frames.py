"""Render a storyboard cut into a 9:16 animatic frame with Pillow.

Each frame is a flat palette card carrying the cut's craft metadata (shot size,
camera move, composition) plus a rule-of-thirds grid — i.e. a readable animatic
panel, not a finished render. This is the visual stand-in until a real
image/video provider fills the seam.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..knowledge.loader import KnowledgeBase
from ..models.storyboard import Cut

try:
    from PIL import Image, ImageDraw, ImageFont

    _PIL_AVAILABLE = True
except ImportError:  # pragma: no cover - exercised only when extra is absent
    _PIL_AVAILABLE = False

_FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
]
_FONT_BOLD_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
]


def pil_available() -> bool:
    return _PIL_AVAILABLE


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    v = value.lstrip("#")
    if len(v) != 6:
        return (40, 40, 48)
    return tuple(int(v[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def _readable_text_color(bg: tuple[int, int, int]) -> tuple[int, int, int]:
    luminance = 0.299 * bg[0] + 0.587 * bg[1] + 0.114 * bg[2]
    return (20, 20, 24) if luminance > 140 else (245, 245, 245)


def _load_font(paths: list[str], size: int) -> Any:
    for path in paths:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _wrap(draw: Any, text: str, font: Any, max_w: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        trial = f"{current} {word}".strip()
        if draw.textlength(trial, font=font) <= max_w:
            current = trial
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines[:6]


def render_cut_frame(
    cut: Cut,
    kb: KnowledgeBase,
    *,
    width: int = 720,
    height: int = 1280,
    title: str = "",
) -> "Image.Image":
    """Render one storyboard cut to a Pillow image (9:16 by default)."""
    if not _PIL_AVAILABLE:  # pragma: no cover
        raise RuntimeError("Pillow is required for rendering. Install the 'render' extra.")

    palette = kb.color_palette(cut.color_mood)
    colors = palette.get("colors") or ["#28303A"]
    bg = _hex_to_rgb(colors[0])
    accent = _hex_to_rgb(colors[-1])
    fg = _readable_text_color(bg)

    img = Image.new("RGB", (width, height), bg)
    draw = ImageDraw.Draw(img)

    # Rule-of-thirds grid (reflects the composition discipline).
    grid = (*accent, 90)
    for i in (1, 2):
        x = width * i // 3
        y = height * i // 3
        draw.line([(x, 0), (x, height)], fill=grid[:3], width=2)
        draw.line([(0, y), (width, y)], fill=grid[:3], width=2)

    font_label = _load_font(_FONT_CANDIDATES, 30)
    font_big = _load_font(_FONT_BOLD_CANDIDATES, 64)
    font_body = _load_font(_FONT_CANDIDATES, 34)

    pad = 40
    draw.text((pad, pad), f"{title}", font=font_label, fill=fg)
    draw.text((pad, pad + 44), f"CUT {cut.index:02d} · {cut.beat_id}", font=font_label, fill=fg)

    # Centre block: shot size + camera move (the staging at a glance).
    draw.text((pad, height // 2 - 120), cut.composition.shot_size, font=font_big, fill=fg)
    draw.text((pad, height // 2 - 40), f"camera: {cut.camera.move_id}", font=font_body, fill=fg)
    draw.text((pad, height // 2 + 6), f"comp: {cut.composition.rule}", font=font_body, fill=fg)
    draw.text((pad, height // 2 + 52), f"light: {cut.lighting}", font=font_body, fill=fg)

    # Description, wrapped, near the lower third.
    y = int(height * 0.70)
    for line in _wrap(draw, cut.description, font_body, width - 2 * pad):
        draw.text((pad, y), line, font=font_body, fill=fg)
        y += 42

    draw.text((pad, height - pad - 30), f"{cut.duration_s:.1f}s", font=font_label, fill=fg)
    return img
