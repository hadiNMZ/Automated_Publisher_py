"""
Shared helpers for TTS providers.

Contains the two things every provider needs:
  - sanitize_for_tts()    — strips characters that TTS engines read aloud
                            (quotes, brackets, parentheses, etc.) instead of
                            ignoring them. gTTS Arabic especially says
                            "فتح قوس / قوس إغلاق" (open bracket / close bracket)
                            and "علامة تنصيص" (quotation mark) for these.
  - concat_with_silence() — joins multiple MP3 segments with a short silence
                            between them via ffmpeg (was duplicated in
                            google_tts and kokoro_tts before).
"""
import re
import subprocess
from pathlib import Path

from config_base import FFMPEG_BINARY

# Apostrophe-like characters: REMOVED entirely (no space) so contractions and
# German forms stay pronounceable: "Wie geht's?" -> "wie gehts", "don't" -> "dont"
_APOSTROPHES = "'\u2019\u02bc\u2018`"

# Invisible/controls: removed silently (zero-width chars, bidi marks)
_INVISIBLE = (
    "\u200b\u200c\u200d\u200e\u200f"
    "\u202a\u202b\u202c\u202d\u202e"
    "\u2066\u2067\u2068\u2069"
    "\ufeff"
)

# Punctuation/symbols TTS engines may announce (quotes, brackets, etc.):
# replaced with a SPACE so words on either side don't get glued together.
# NOTE: kept out of this list on purpose: . , ! ? : ; - – — ، ؟
# (those render as natural pauses and help pacing; hyphen keeps
# pronunciation notes like "ap-fl" sounding right).
_TO_SPACE = (
    '"\u201c\u201d\u201e\u201f\u00ab\u00bb\u2039\u203a'  # straight/curly/guillemet quotes
    '()\uff08\uff09[\u005b\u005d{}<>\u3010\u3011'          # brackets/parens (ascii+fullwidth)
    '\u2026\u2022*_#=~|^\u00b0\u00a7\u00a4\u2020\u2021/\\'  # misc symbols TTS may spell out
    '+\u00d7\u00f7\u2264\u2265\u2192\u2190'
)


def sanitize_for_tts(text: str) -> str:
    """
    Cleans a TTS segment so engines never read symbol names aloud
    ("quote", "bracket", "open paren", ...). Also collapses whitespace.

    Applied to every segment by tts_registry before dispatching to any
    provider, so all providers benefit automatically.
    """
    if not text:
        return text

    # 1) Remove apostrophes + invisible chars entirely
    for ch in _APOSTROPHES + _INVISIBLE:
        text = text.replace(ch, "")

    # 2) Replace noisy punctuation with spaces
    text = re.sub("[" + re.escape(_TO_SPACE) + "]", " ", text)

    # 3) Tidy: no space before sentence punctuation (from removals like
    #    "Anna" . -> Anna .)
    text = re.sub(r"\s+([.,!?;:،؟])", r"\1", text)

    # 4) Collapse whitespace runs, trim
    text = re.sub(r"\s+", " ", text).strip()
    return text


def concat_with_silence(
    input_paths: list[Path],
    output_path: Path,
    silence_duration: float = 0.3,
) -> None:
    """
    Concatenates audio files with silence between them using ffmpeg.

    For N input files, builds a filter graph:
        [0:a][silence][1:a][silence][2:a]...concat=n=(2N-1):v=0:a=1[out]

    Each silence is an anullsrc input of `silence_duration` seconds.
    """
    cmd = [FFMPEG_BINARY, "-y"]
    filter_parts = []
    input_idx = 0

    for i, audio_path in enumerate(input_paths):
        # Add the audio input
        cmd.extend(["-i", str(audio_path)])
        filter_parts.append(f"[{input_idx}:a]")
        input_idx += 1

        # Add silence between segments (not after the last one)
        if i < len(input_paths) - 1:
            cmd.extend([
                "-f", "lavfi",
                "-t", str(silence_duration),
                "-i", "anullsrc=r=44100:cl=mono",
            ])
            filter_parts.append(f"[{input_idx}:a]")
            input_idx += 1

    n_concat = len(filter_parts)
    filter_complex = "".join(filter_parts) + f"concat=n={n_concat}:v=0:a=1[out]"

    cmd.extend([
        "-filter_complex", filter_complex,
        "-map", "[out]",
        "-c:a", "libmp3lame",
        "-q:a", "2",
        str(output_path),
    ])

    result = subprocess.run(
        cmd, capture_output=True, text=True, stdin=subprocess.DEVNULL
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"ffmpeg concat failed (exit {result.returncode}).\n"
            f"Command: {' '.join(cmd)}\n\nffmpeg stderr:\n{result.stderr}"
        )
