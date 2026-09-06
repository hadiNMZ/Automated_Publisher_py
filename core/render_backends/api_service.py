"""
TEMPLATE for a future rendering API (Creatomate, Shotstack, JSON2Video,
etc). Same interface as ffmpeg_local.render() so pipeline.py never
needs to change when you switch RENDER_BACKEND=api_service in .env.

Fill this in once you've picked a service:
  1. Add RENDER_API_URL and RENDER_API_KEY to config_base.py / .env
  2. Implement render() below to call that API and download the result
     to output_path
  3. Set RENDER_BACKEND=api_service in .env
"""
from pathlib import Path


def render(text_lines: list[str], audio_path: Path, output_path: Path,
           font_bold: str, font_regular: str, duration: int = 8) -> Path:
    raise NotImplementedError(
        "Implement this once you've chosen a rendering API. "
        "Same signature as ffmpeg_local.render() so nothing else changes."
    )
