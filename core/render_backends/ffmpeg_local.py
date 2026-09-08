"""
Legacy single-slide drawtext renderer — does NOT support multi-slide or Arabic.
Kept for backwards compat. Use pillow_overlay for the full feature set.
"""
import subprocess
from pathlib import Path
from config_base import FFMPEG_BINARY


def _escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")


def _run_ffmpeg(cmd: list[str]) -> None:
    result = subprocess.run(cmd, capture_output=True, text=True, stdin=subprocess.DEVNULL)
    if result.returncode != 0:
        raise RuntimeError(
            f"ffmpeg failed (exit {result.returncode}).\n"
            f"Command: {' '.join(cmd)}\n\nffmpeg stderr:\n{result.stderr}"
        )


def render(slides: list[dict], audio_path: Path, output_path: Path,
           font_bold: str, font_regular: str, font_arabic: str = "",
           duration: float = 30) -> Path:
    """
    Legacy fallback — renders only the first slide as a single image.
    Does NOT support crossfade, multi-slide, or Arabic text.
    Use RENDER_BACKEND=pillow_overlay for full features.
    """
    import warnings
    warnings.warn(
        "ffmpeg_local does not support multi-slide rendering or Arabic text. "
        "Set RENDER_BACKEND=pillow_overlay in .env for full features.",
        UserWarning
    )

    # Just render the first slide as a single video
    first_slide = slides[0] if slides else {"render_plan": [], "duration": duration}
    plan = first_slide.get("render_plan", [])
    slide_dur = first_slide.get("duration", duration)

    filters = []
    y = 100
    for item in plan:
        text = item.get("text", "")
        if not text:
            continue
        font = font_bold if item.get("type") in ("main", "section_header") else font_regular
        size = 50 if item.get("type") == "main" else 35
        color = "white" if item.get("type") != "arabic" else "0xc8dcff"
        filters.append(
            f"drawtext=fontfile={font}:text='{_escape(text)}':fontcolor={color}:"
            f"fontsize={size}:x=(w-text_w)/2:y={y}"
        )
        y += 80

    vf = ",".join(filters) if filters else "null"
    background_path = output_path.parent / "background.mp4"

    _run_ffmpeg([
        FFMPEG_BINARY, "-y",
        "-f", "lavfi", "-i", f"color=c=0x1e1e2f:s=1080x1920:d={slide_dur}",
        "-vf", vf,
        "-c:v", "libx264", "-t", str(slide_dur),
        str(background_path),
    ])

    _run_ffmpeg([
        FFMPEG_BINARY, "-y",
        "-i", str(background_path),
        "-i", str(audio_path),
        "-c:v", "copy", "-c:a", "aac", "-shortest",
        str(output_path),
    ])

    return output_path
