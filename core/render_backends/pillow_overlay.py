"""
Pillow + ffmpeg overlay renderer — a more robust alternative to ffmpeg's
drawtext filter. Renders text to a transparent PNG using Pillow (which
has its own font rendering, supports any Unicode character, and handles
text wrapping properly), then composites that PNG onto a solid-color
video background using ffmpeg's `overlay` filter.

Why this exists:
  - ffmpeg's drawtext filter requires libfreetype+libfontconfig at build
    time. Some distro ffmpeg packages (notably Fedora/RPM Fusion builds
    and some custom builds) omit it, producing "No such filter: 'drawtext'".
  - The `overlay` filter is in every ffmpeg build (no optional deps), so
    this renderer works regardless of how ffmpeg was compiled.
  - Pillow does its own text rendering with FreeType, so we get proper
    German/French/Spanish accented chars + Arabic + emoji if needed.
  - Side benefit: proper text wrapping (long example sentences split
    across multiple lines instead of overflowing the frame).

Same signature as ffmpeg_local.render() so it drops in via .env:
    RENDER_BACKEND=pillow_overlay
"""
import subprocess
import textwrap
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

from config_base import FFMPEG_BINARY


# --- Layout constants (1080x1920 vertical Short) ---
FRAME_W = 1080
FRAME_H = 1920
BG_COLOR = (30, 30, 47)  # 0x1e1e2f

# Vertical anchor where the text block starts
TOP_Y = 550

# Per-line vertical spacing
LINE_SPACING = 150

# Per-role styling (matches what ffmpeg_local used to do, but cleaner)
STYLE_BOLD = "bold"
STYLE_MUTED = "muted"
STYLE_REGULAR = "regular"

# Maximum chars per line for the example sentence (small font, lots of room)
EXAMPLE_WRAP_WIDTH = 42


def _run_ffmpeg(cmd: list[str]) -> None:
    """Runs ffmpeg and raises a readable error with stderr on failure.
    stdin is explicitly closed (DEVNULL) because ffmpeg otherwise waits
    on stdin forever when invoked from a non-interactive context."""
    result = subprocess.run(
        cmd, capture_output=True, text=True,
        stdin=subprocess.DEVNULL,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"ffmpeg failed (exit {result.returncode}).\n"
            f"Command: {' '.join(cmd)}\n\nffmpeg stderr:\n{result.stderr}"
        )


def _load_font(font_path: str, size: int) -> ImageFont.FreeTypeFont:
    if not Path(font_path).exists():
        raise FileNotFoundError(f"Font file not found: {font_path}")
    return ImageFont.truetype(font_path, size)


def _render_text_png(
    text_lines: list[str],
    output_png: Path,
    font_bold: str,
    font_regular: str,
) -> None:
    """
    Renders text_lines to a transparent PNG sized FRAME_W x FRAME_H.
    First line = bold + large. Second line = regular + muted gray.
    Remaining lines = regular + white, auto-wrapped if too long.

    Lines are stacked vertically starting at TOP_Y, centered horizontally.
    """
    img = Image.new("RGBA", (FRAME_W, FRAME_H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    y = TOP_Y
    for i, line in enumerate(text_lines):
        if i == 0:
            # Main word/phrase — bold, large, white
            font = _load_font(font_bold, 90)
            color = (255, 255, 255, 255)
            sub_lines = [line]
            line_height = 110
        elif i == 1:
            # Translation — regular, medium, muted gray
            font = _load_font(font_regular, 55)
            color = (204, 204, 204, 255)
            sub_lines = [line]
            line_height = 80
        else:
            # Example sentence — regular, small, white, auto-wrapped
            font = _load_font(font_regular, 45)
            color = (255, 255, 255, 255)
            sub_lines = textwrap.wrap(line, width=EXAMPLE_WRAP_WIDTH) or [line]
            line_height = 65

        for sub_line in sub_lines:
            # Center horizontally
            bbox = draw.textbbox((0, 0), sub_line, font=font)
            text_w = bbox[2] - bbox[0]
            x = (FRAME_W - text_w) // 2
            draw.text((x, y), sub_line, fill=color, font=font)
            y += line_height

        # Extra gap between top-level lines
        y += LINE_SPACING - (line_height * len(sub_lines))

    img.save(str(output_png), "PNG")


def _build_background(duration: int, output_path: Path) -> None:
    """Creates the solid-color video background using lavfi color source."""
    _run_ffmpeg([
        FFMPEG_BINARY, "-y",
        "-f", "lavfi", "-i", f"color=c=0x1e1e2f:s={FRAME_W}x{FRAME_H}:d={duration}",
        "-c:v", "libx264", "-t", str(duration),
        "-pix_fmt", "yuv420p",
        str(output_path),
    ])


def _overlay_and_mux(
    background_path: Path,
    overlay_png: Path,
    audio_path: Path,
    output_path: Path,
    duration: int,
) -> None:
    """
    Overlays the text PNG onto the background video, then muxes with audio.
    Uses the `overlay` filter (always present in ffmpeg) instead of drawtext.
    """
    # Single ffmpeg pass: take background video + PNG overlay + audio,
    # produce final video with overlay burned in and audio muxed.
    _run_ffmpeg([
        FFMPEG_BINARY, "-y",
        "-i", str(background_path),
        "-i", str(overlay_png),
        "-i", str(audio_path),
        "-filter_complex",
        "[0:v][1:v]overlay=0:0:format=auto[v]",
        "-map", "[v]", "-map", "2:a",
        "-c:v", "libx264", "-c:a", "aac",
        "-t", str(duration),
        "-pix_fmt", "yuv420p",
        str(output_path),
    ])


def render(
    text_lines: list[str],
    audio_path: Path,
    output_path: Path,
    font_bold: str,
    font_regular: str,
    duration: int = 8,
) -> Path:
    """
    Renders a vertical Short with text overlay + audio.

    Same signature as ffmpeg_local.render() so pipeline.py doesn't need
    any changes — just set RENDER_BACKEND=pillow_overlay in .env.

    text_lines: list of strings to stack vertically. First line is the
        main word/phrase (bold large). Second line is translation (muted
        gray). Remaining lines are example sentences (white, auto-wrapped).
    audio_path: path to the TTS-generated audio file.
    output_path: where to write the final video.
    font_bold, font_regular: paths to .ttf files.
    duration: video length in seconds (matches audio length typically).
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    background_path = output_path.parent / "background.mp4"
    overlay_png = output_path.parent / "text_overlay.png"

    print(f"  [pillow_overlay] Rendering text PNG with {len(text_lines)} lines...")
    _render_text_png(text_lines, overlay_png, font_bold, font_regular)

    print(f"  [pillow_overlay] Building {duration}s background...")
    _build_background(duration, background_path)

    print(f"  [pillow_overlay] Overlaying text + muxing audio...")
    _overlay_and_mux(background_path, overlay_png, audio_path, output_path, duration)

    return output_path
