"""
Registry: RENDER_BACKEND in .env picks which backend actually renders.
- "pillow_overlay" — multi-slide renderer with Arabic font support + crossfade (recommended)
- "ffmpeg_local"   — single-slide drawtext (legacy, no Arabic support)
- "api_service"    — template for a future rendering API

Task 2 update: render() now accepts a "slides" list (each slide has a
render_plan + duration) + font_arabic path, instead of a single render_plan.
"""
from pathlib import Path
from config_base import RENDER_BACKEND
from . import ffmpeg_local, pillow_overlay, api_service

BACKENDS = {
    "pillow_overlay": pillow_overlay.render,
    "ffmpeg_local": ffmpeg_local.render,
    "api_service": api_service.render,
}


def render(slides: list[dict], audio_path: Path, output_path: Path,
           font_bold: str, font_regular: str, font_arabic: str = "",
           duration: float = 30) -> Path:
    fn = BACKENDS.get(RENDER_BACKEND)
    if fn is None:
        raise ValueError(f"Unknown RENDER_BACKEND '{RENDER_BACKEND}' — available: {list(BACKENDS)}")
    return fn(slides, audio_path, output_path, font_bold, font_regular, font_arabic, duration)
