"""
gTTS-based TTS with multilingual segment support.

Task 1b update: adds generate_segments() which calls gTTS separately
for each (text, lang) segment, then concatenates the resulting MP3s
with short silence between them for natural pacing.

This is the key fix for the "English read in a German accent" problem:
each segment is generated with the correct gTTS language code, so
English text is read in English, Arabic in Arabic, German in German,
etc. — all in one audio file.

Requires ffmpeg for concatenation (already a project dependency).
"""
import subprocess
import tempfile
from pathlib import Path
from gtts import gTTS


def generate(text: str, lang_or_voice: str, output_path: Path) -> Path:
    """Old single-text interface — generates one gTTS call in one language."""
    tts = gTTS(text=text, lang=lang_or_voice)
    tts.save(str(output_path))
    return output_path


def generate_segments(
    segments: list[tuple[str, str]],
    lang_or_voice: str,
    output_path: Path,
) -> Path:
    """
    Multilingual TTS: generates one MP3 per segment, concatenates with
    0.3s silence between segments.

    segments: list of (text, lang_code) tuples where lang_code is a
        gTTS language code ("de", "en", "ar", "fr", "es", etc.)
    lang_or_voice: ignored (each segment has its own lang_code). Kept
        in the signature for consistency with other TTS providers.
    output_path: final combined MP3 path.
    """
    # Filter out empty segments
    segments = [(text, lang) for text, lang in segments if text and text.strip()]
    if not segments:
        raise ValueError("No non-empty TTS segments provided")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Generate each segment as a temporary MP3
    temp_files = []
    for i, (text, lang) in enumerate(segments):
        temp_path = output_path.parent / f"_tts_segment_{i}.mp3"
        try:
            tts = gTTS(text=text, lang=lang)
            tts.save(str(temp_path))
            temp_files.append(temp_path)
        except Exception as e:
            # If a specific language fails (e.g. unsupported lang),
            # skip that segment rather than failing the whole pipeline
            print(f"  [google_tts] WARNING: segment {i} (lang={lang}) failed: {e}")
            if temp_path.exists():
                temp_path.unlink()

    if not temp_files:
        raise RuntimeError("All TTS segments failed to generate")

    if len(temp_files) == 1:
        # Only one segment — just rename it
        import shutil
        shutil.copy(str(temp_files[0]), str(output_path))
        temp_files[0].unlink()
        return output_path

    # Concatenate all segments with 0.3s silence between them
    _concat_with_silence(temp_files, output_path, silence_duration=0.3)

    # Cleanup temp files
    for tf in temp_files:
        if tf.exists():
            tf.unlink()

    return output_path


def _concat_with_silence(
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
    cmd = ["ffmpeg", "-y"]
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
