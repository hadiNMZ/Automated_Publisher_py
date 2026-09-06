"""
Registry: RENDER_BACKEND in .env picks which backend actually renders.
"ffmpeg_local" today (for testing); "api_service" once you've wired up
a rendering API — see api_service.py's docstring.
"""
from pathlib import Path
from config_base import RENDER_BACKEND
from . import ffmpeg_local, api_service

BACKENDS = {
    "ffmpeg_local": ffmpeg_local.render,
    "api_service": api_service.render,
}


def render(text_lines: list[str], audio_path: Path, output_path: Path,
           font_bold: str, font_regular: str, duration: int = 8) -> Path:
    fn = BACKENDS.get(RENDER_BACKEND)
    if fn is None:
        raise ValueError(f"Unknown RENDER_BACKEND '{RENDER_BACKEND}' — available: {list(BACKENDS)}")
    return fn(text_lines, audio_path, output_path, font_bold, font_regular, duration)
