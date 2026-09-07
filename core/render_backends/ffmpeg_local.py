"""
Local ffmpeg rendering — the "for testing" backend. Takes generic text
lines (not hardcoded to German) so any language plugin can use it.
Requires ffmpeg installed and on PATH (or FFMPEG_BINARY pointing at a
working build — see README if you hit a "No such filter: drawtext"
error, which means your system ffmpeg is broken/mismatched).
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


def render(text_lines: list[str], audio_path: Path, output_path: Path,
           font_bold: str, font_regular: str, duration: int = 8) -> Path:
    """
    text_lines: list of strings to stack vertically, largest/first line
    styled bold, the rest regular. Typically [word, translation(s),
    example]. Caller decides what goes in — this module just lays them
    out.
    """
    for font_path in (font_bold, font_regular):
        if not Path(font_path).exists():
            raise FileNotFoundError(f"Font file not found: {font_path}")

    filters = []
    y = 550
    for i, line in enumerate(text_lines):
        font = font_bold if i == 0 else font_regular
        size = 90 if i == 0 else (55 if i == 1 else 40)
        color = "white" if i != 1 else "0xcccccc"
        filters.append(
            f"drawtext=fontfile={font}:text='{_escape(line)}':fontcolor={color}:"
            f"fontsize={size}:x=(w-text_w)/2:y={y}"
        )
        y += 150

    vf = ",".join(filters)
    background_path = output_path.parent / "background.mp4"

    _run_ffmpeg([
        FFMPEG_BINARY, "-y",
        "-f", "lavfi", "-i", f"color=c=0x1e1e2f:s=1080x1920:d={duration}",
        "-vf", vf,
        "-c:v", "libx264", "-t", str(duration),
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
