"""
Multi-slide Pillow + ffmpeg renderer with Arabic font support and crossfade transitions.

Renders 3 slides (Grammar, Word of the Day, Examples) as separate PNGs,
builds a background video per slide, overlays text, then crossfades the
slides together using ffmpeg's xfade filter.

Arabic text rendering: uses Noto Sans Arabic font (passed by the pipeline)
as a fallback for Arabic characters that Inter doesn't support. The font
fallback is handled per-character: if Inter doesn't have a glyph, Noto
Sans Arabic is used for that character.

Architecture:
    1. For each slide: Pillow renders text to a transparent PNG
    2. For each slide: ffmpeg builds a solid-color background video
    3. For each slide: ffmpeg overlays the PNG onto the background
    4. ffmpeg xfade crossfades the 3 slide videos into one
    5. ffmpeg muxes the concatenated audio with the final video
"""
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

from config_base import FFMPEG_BINARY

# --- Layout constants (1080x1920 vertical Short) ---
FRAME_W = 1080
FRAME_H = 1920
BG_COLOR = (30, 30, 47)  # 0x1e1e2f

# Colors
COLOR_WHITE = (255, 255, 255, 255)
COLOR_MUTED = (180, 180, 200, 255)
COLOR_ACCENT = (130, 170, 255, 255)
COLOR_ARABIC = (200, 220, 255, 255)  # slightly different tint for Arabic
COLOR_HEADER = (150, 150, 170, 255)
COLOR_DIVIDER = (80, 80, 110, 255)

# Vertical layout
TOP_PADDING = 80
SECTION_GAP = 40
HEADER_DIVIDER_GAP = 6
POST_HEADER_GAP = 20
LINE_GAP = 10
EXAMPLE_GAP = 16

# Font sizes
SIZE_HEADER = 28          # "German | A1" at top
SIZE_SECTION_HEADER = 30  # "GRAMMAR RULE", "WORD OF THE DAY", etc.
SIZE_MAIN = 48            # Rule name, word, example sentences
SIZE_ARABIC = 36          # Arabic translations
SIZE_LABEL = 28           # "pronunciation", "noun male", etc.
SIZE_MUTED = 24           # Pronunciation guide, metadata

# Crossfade duration between slides
XFADE_DURATION = 0.5


def _run_ffmpeg(cmd: list[str]) -> None:
    result = subprocess.run(cmd, capture_output=True, text=True, stdin=subprocess.DEVNULL)
    if result.returncode != 0:
        raise RuntimeError(
            f"ffmpeg failed (exit {result.returncode}).\n"
            f"Command: {' '.join(cmd)}\n\nffmpeg stderr:\n{result.stderr}"
        )


def _load_font(font_path: str, size: int) -> ImageFont.FreeTypeFont:
    if not Path(font_path).exists():
        raise FileNotFoundError(f"Font file not found: {font_path}")
    return ImageFont.truetype(font_path, size)


def _has_arabic(text: str) -> bool:
    """Check if text contains Arabic characters."""
    for char in text:
        if '\u0600' <= char <= '\u06FF' or '\u0750' <= char <= '\u077F':
            return True
    return False


def _draw_text_with_fallback(
    draw: ImageDraw.ImageDraw,
    text: str,
    font_latin: ImageFont.FreeTypeFont,
    font_arabic: ImageFont.FreeTypeFont,
    x: int,
    y: int,
    color,
) -> int:
    """Draws text, using Arabic font for Arabic characters and Latin font
    for everything else. Returns y position after drawing."""
    if not text:
        return y

    if _has_arabic(text):
        # Draw the whole text with Arabic font
        draw.text((x, y), text, fill=color, font=font_arabic)
        bbox = draw.textbbox((x, y), text, font=font_arabic)
        return bbox[3] + 4
    else:
        draw.text((x, y), text, fill=color, font=font_latin)
        bbox = draw.textbbox((x, y), text, font=font_latin)
        return bbox[3] + 4


def _wrap_text_by_pixels(
    text: str, font, draw: ImageDraw.ImageDraw, max_width: int
) -> list[str]:
    """Wraps text to fit within max_width pixels using word-by-word measurement."""
    words = text.split()
    if not words:
        return [text]
    lines = []
    current_line = words[0]
    for word in words[1:]:
        test_line = current_line + " " + word
        if draw.textlength(test_line, font=font) <= max_width:
            current_line = test_line
        else:
            lines.append(current_line)
            current_line = word
    lines.append(current_line)
    return lines


def _draw_centered(
    draw: ImageDraw.ImageDraw,
    text: str,
    font, y: int, color,
    max_width: int = FRAME_W - 80,
) -> int:
    text_w = draw.textlength(text, font=font)
    if text_w > max_width:
        x = 40
    else:
        x = (FRAME_W - text_w) // 2
    bbox = draw.textbbox((0, 0), text, font=font)
    text_h = bbox[3] - bbox[1]
    draw.text((x, y), text, fill=color, font=font)
    return y + text_h


def _draw_divider(draw: ImageDraw.ImageDraw, y: int, width: int = 180) -> int:
    x_start = (FRAME_W - width) // 2
    x_end = x_start + width
    draw.line([(x_start, y), (x_end, y)], fill=COLOR_DIVIDER, width=2)
    return y + HEADER_DIVIDER_GAP


def _render_slide_png(
    render_plan: list[dict],
    output_png: Path,
    font_bold: str,
    font_regular: str,
    font_arabic: str,
) -> None:
    """Renders one slide's text to a transparent PNG."""
    img = Image.new("RGBA", (FRAME_W, FRAME_H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    fonts = {
        "header": _load_font(font_regular, SIZE_HEADER),
        "section_header": _load_font(font_bold, SIZE_SECTION_HEADER),
        "main": _load_font(font_bold, SIZE_MAIN),
        "arabic": _load_font(font_arabic, SIZE_ARABIC),
        "label": _load_font(font_regular, SIZE_LABEL),
        "muted": _load_font(font_regular, SIZE_MUTED),
    }

    max_text_width = FRAME_W - 80
    y = TOP_PADDING

    for item in render_plan:
        line_type = item["type"]
        text = item.get("text", "")
        if not text:
            continue

        if line_type == "header":
            y = _draw_centered(draw, text, fonts["header"], y, COLOR_HEADER)
            y += 20

        elif line_type == "section_header":
            if y > TOP_PADDING + 30:
                y += SECTION_GAP
            y = _draw_centered(draw, text.upper(), fonts["section_header"], y, COLOR_ACCENT)
            y = _draw_divider(draw, y + 2)
            y += POST_HEADER_GAP

        elif line_type == "main":
            font = fonts["main"]
            for sub_line in _wrap_text_by_pixels(text, font, draw, max_text_width):
                y = _draw_centered(draw, sub_line, font, y, COLOR_WHITE)
                y += LINE_GAP
            y += 6

        elif line_type == "arabic":
            font = fonts["arabic"]
            for sub_line in _wrap_text_by_pixels(text, font, draw, max_text_width):
                y = _draw_centered(draw, sub_line, font, y, COLOR_ARABIC)
                y += LINE_GAP
            y += 6

        elif line_type == "label":
            y = _draw_centered(draw, text, fonts["label"], y, COLOR_ACCENT)
            y += 4

        elif line_type == "translation":
            font = fonts["main"]
            for sub_line in _wrap_text_by_pixels(text, font, draw, max_text_width):
                y = _draw_centered(draw, sub_line, font, y, COLOR_WHITE)
                y += LINE_GAP
            y += 4

        elif line_type == "muted":
            font = fonts["muted"]
            for sub_line in _wrap_text_by_pixels(text, font, draw, max_text_width):
                y = _draw_centered(draw, sub_line, font, y, COLOR_MUTED)
                y += LINE_GAP - 2

        elif line_type == "example_gap":
            y += EXAMPLE_GAP

    img.save(str(output_png), "PNG")


def _build_background(duration: float, output_path: Path) -> None:
    _run_ffmpeg([
        FFMPEG_BINARY, "-y",
        "-f", "lavfi", "-i", f"color=c=0x1e1e2f:s={FRAME_W}x{FRAME_H}:d={duration}",
        "-c:v", "libx264", "-t", str(duration),
        "-pix_fmt", "yuv420p",
        str(output_path),
    ])


def _overlay_text(background_path: Path, overlay_png: Path, output_path: Path, duration: float) -> None:
    _run_ffmpeg([
        FFMPEG_BINARY, "-y",
        "-i", str(background_path),
        "-i", str(overlay_png),
        "-filter_complex",
        f"[0:v][1:v]overlay=0:0:format=auto[v]",
        "-map", "[v]",
        "-c:v", "libx264",
        "-t", str(duration),
        "-pix_fmt", "yuv420p",
        str(output_path),
    ])


def _crossfade_slides(slide_videos: list[Path], slide_durations: list[float], output_path: Path) -> None:
    """Crossfades multiple slide videos into one using ffmpeg xfade filter."""
    if len(slide_videos) == 1:
        import shutil
        shutil.copy(str(slide_videos[0]), str(output_path))
        return

    # Build xfade chain: [0][1]xfade -> [v1]; [v1][2]xfade -> [v2]; etc.
    filter_parts = []
    prev_label = "[0:v]"
    offset = slide_durations[0] - XFADE_DURATION

    for i in range(1, len(slide_videos)):
        # xfade offset = cumulative duration of previous slides minus cumulative xfade durations
        # offset = sum(durations[0..i-1]) - i * XFADE_DURATION
        offset = sum(slide_durations[:i]) - i * XFADE_DURATION
        out_label = f"[v{i}]" if i < len(slide_videos) - 1 else "[vout]"
        filter_parts.append(
            f"{prev_label}[{i}:v]xfade=transition=fade:duration={XFADE_DURATION}:offset={offset:.2f}{out_label}"
        )
        prev_label = out_label

    filter_complex = ";".join(filter_parts)

    cmd = [FFMPEG_BINARY, "-y"]
    for sv in slide_videos:
        cmd.extend(["-i", str(sv)])
    cmd.extend([
        "-filter_complex", filter_complex,
        "-map", "[vout]",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        str(output_path),
    ])
    _run_ffmpeg(cmd)


def render(
    slides: list[dict],
    audio_path: Path,
    output_path: Path,
    font_bold: str,
    font_regular: str,
    font_arabic: str = "",
    duration: float = 30,
) -> Path:
    """
    Renders a multi-slide video with crossfade transitions.

    slides: list of slide dicts, each with:
        - "render_plan": list of styled line dicts (see _render_slide_png)
        - "duration": how long this slide stays on screen (seconds)
    audio_path: path to the full concatenated TTS audio
    output_path: final video output path
    font_bold, font_regular: paths to Latin fonts (Inter)
    font_arabic: path to Arabic font (Noto Sans Arabic). Required for Arabic text.
    duration: total video duration (should match audio duration)
    """
    if not font_arabic:
        raise ValueError(
            "font_arabic path is required for the multi-slide renderer. "
            "Add a Noto Sans Arabic font to the plugin's assets/ folder."
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    temp_dir = output_path.parent / "_temp_slides"
    temp_dir.mkdir(exist_ok=True)

    slide_videos = []
    slide_durations = []

    for i, slide in enumerate(slides):
        plan = slide["render_plan"]
        slide_dur = slide["duration"]

        overlay_png = temp_dir / f"slide_{i}_overlay.png"
        bg_path = temp_dir / f"slide_{i}_bg.mp4"
        slide_video = temp_dir / f"slide_{i}.mp4"

        print(f"  [pillow_overlay] Slide {i+1}/{len(slides)}: rendering PNG ({len(plan)} items)...")
        _render_slide_png(plan, overlay_png, font_bold, font_regular, font_arabic)

        print(f"  [pillow_overlay] Slide {i+1}: building {slide_dur:.1f}s background...")
        _build_background(slide_dur, bg_path)

        print(f"  [pillow_overlay] Slide {i+1}: overlaying text...")
        _overlay_text(bg_path, overlay_png, slide_video, slide_dur)

        slide_videos.append(slide_video)
        slide_durations.append(slide_dur)

    if len(slide_videos) > 1:
        print(f"  [pillow_overlay] Crossfading {len(slide_videos)} slides...")
        video_no_audio = temp_dir / "crossfaded.mp4"
        _crossfade_slides(slide_videos, slide_durations, video_no_audio)
    else:
        video_no_audio = slide_videos[0]

    print(f"  [pillow_overlay] Muxing audio...")
    _run_ffmpeg([
        FFMPEG_BINARY, "-y",
        "-i", str(video_no_audio),
        "-i", str(audio_path),
        "-c:v", "copy", "-c:a", "aac",
        "-shortest",
        "-pix_fmt", "yuv420p",
        str(output_path),
    ])

    # Cleanup temp files
    import shutil
    shutil.rmtree(str(temp_dir), ignore_errors=True)

    return output_path
