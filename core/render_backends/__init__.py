"""
Registry: RENDER_BACKEND in .env picks which backend actually renders.
- "ffmpeg_local"   — uses ffmpeg's drawtext filter (requires ffmpeg built
                     with libfreetype; breaks on some distro builds)
- "pillow_overlay" — renders text via Pillow, composites with ffmpeg's
                     overlay filter (works on every ffmpeg build, handles
                     text wrapping, recommended)
- "api_service"    — template for a future rendering API
"""
from pathlib import Path
from config_base import RENDER_BACKEND
from . import ffmpeg_local, pillow_overlay, api_service

BACKENDS = {
    "ffmpeg_local": ffmpeg_local.render,
    "pillow_overlay": pillow_overlay.render,
    "api_service": api_service.render,
}


def render(text_lines: list[str], audio_path: Path, output_path: Path,
           font_bold: str, font_regular: str, duration: int = 8) -> Path:
    fn = BACKENDS.get(RENDER_BACKEND)
    if fn is None:
        raise ValueError(f"Unknown RENDER_BACKEND '{RENDER_BACKEND}' — available: {list(BACKENDS)}")
    return fn(text_lines, audio_path, output_path, font_bold, font_regular, duration)
