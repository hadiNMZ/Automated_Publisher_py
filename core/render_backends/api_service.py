"""
TEMPLATE for a future rendering API (Creatomate, Shotstack, JSON2Video).
Same interface as pillow_overlay so pipeline.py never needs to change.

Task 2 update: signature now accepts slides list + font_arabic.
When you implement this, convert the slides into the API's JSON format.
"""
import requests
from pathlib import Path
from config_base import RENDER_API_URL, RENDER_API_KEY


def _convert_slides_to_api_format(slides: list[dict]) -> list[dict]:
    """PLACEHOLDER: Convert slides to your rendering API's JSON format."""
    result = []
    for slide in slides:
        result.append({
            "duration": slide.get("duration", 10),
            "scenes": [
                {"text": item.get("text", ""), "type": item.get("type", "")}
                for item in slide.get("render_plan", [])
            ]
        })
    return result


def render(slides: list[dict], audio_path: Path, output_path: Path,
           font_bold: str, font_regular: str, font_arabic: str = "",
           duration: float = 30) -> Path:
    """
    PLACEHOLDER: Calls an external rendering API.

    When implementing:
      1. Convert slides to the API's JSON format
      2. POST to RENDER_API_URL with RENDER_API_KEY auth
      3. Poll for completion (or use webhook)
      4. Download the rendered video to output_path
    """
    if not RENDER_API_URL:
        raise RuntimeError(
            "RENDER_API_URL is not set. Use RENDER_BACKEND=pillow_overlay for local rendering."
        )

    api_payload = {
        "total_duration": duration,
        "slides": _convert_slides_to_api_format(slides),
        "audio": str(audio_path),
        "fonts": {"bold": font_bold, "regular": font_regular, "arabic": font_arabic},
    }

    raise NotImplementedError(
        "api_service.render() is a placeholder. Implement it for your chosen "
        "rendering API, or set RENDER_BACKEND=pillow_overlay in .env."
    )
