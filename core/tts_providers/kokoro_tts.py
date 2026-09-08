"""
Kokoro local TTS server with multilingual segment support.

Task 1b update: adds generate_segments(). Kokoro-82M is English-only,
so non-English segments are SKIPPED (with a warning). Only English
segments are generated and concatenated.

This means: for the German plugin with Kokoro, only the English
translation/explanation parts will be read aloud — the German words
and sentences will be silent. This is why Kokoro is recommended only
for the English plugin or English-language niches (gaming, streamer).
"""
import subprocess
import requests
from pathlib import Path
from config_base import KOKORO_API_URL


def generate(text: str, lang_or_voice: str, output_path: Path) -> Path:
    """Old single-text interface."""
    payload = {"model": "kokoro", "input": text, "voice": lang_or_voice, "response_format": "mp3"}
    resp = requests.post(KOKORO_API_URL, json=payload, timeout=60)
    resp.raise_for_status()
    output_path.write_bytes(resp.content)
    return output_path


def generate_segments(
    segments: list[tuple[str, str]],
    lang_or_voice: str,
    output_path: Path,
) -> Path:
    """
    Kokoro is English-only. Filters segments to English-only, generates
    each one, and concatenates with silence between.

    Non-English segments are skipped with a warning printed to console.
    """
    # Kokoro only supports English
    english_segments = [(text, lang) for text, lang in segments if lang == "en" and text and text.strip()]
    skipped = [lang for text, lang in segments if lang != "en" and text and text.strip()]

    if skipped:
        print(f"  [kokoro] WARNING: skipping {len(skipped)} non-English segment(s) "
              f"(languages: {set(skipped)}). Kokoro is English-only.")

    if not english_segments:
        raise RuntimeError(
            "No English segments to generate. Kokoro only supports English. "
            "Use TTS_PROVIDER=google for multilingual support."
        )

    # Generate each English segment
    temp_files = []
    for i, (text, _) in enumerate(english_segments):
        temp_path = output_path.parent / f"_tts_segment_{i}.mp3"
        try:
            payload = {"model": "kokoro", "input": text, "voice": lang_or_voice, "response_format": "mp3"}
            resp = requests.post(KOKORO_API_URL, json=payload, timeout=60)
            resp.raise_for_status()
            temp_path.write_bytes(resp.content)
            temp_files.append(temp_path)
        except Exception as e:
            print(f"  [kokoro] WARNING: segment {i} failed: {e}")
            if temp_path.exists():
                temp_path.unlink()

    if not temp_files:
        raise RuntimeError("All Kokoro TTS segments failed to generate")

    if len(temp_files) == 1:
        import shutil
        shutil.copy(str(temp_files[0]), str(output_path))
        temp_files[0].unlink()
        return output_path

    # Concatenate with silence between
    _concat_with_silence(temp_files, output_path, silence_duration=0.3)

    # Cleanup
    for tf in temp_files:
        if tf.exists():
            tf.unlink()

    return output_path


def _concat_with_silence(input_paths: list[Path], output_path: Path, silence_duration: float = 0.3):
    """Same concat logic as google_tts — duplicated to avoid cross-provider imports."""
    cmd = ["ffmpeg", "-y"]
    filter_parts = []
    input_idx = 0

    for i, audio_path in enumerate(input_paths):
        cmd.extend(["-i", str(audio_path)])
        filter_parts.append(f"[{input_idx}:a]")
        input_idx += 1
        if i < len(input_paths) - 1:
            cmd.extend(["-f", "lavfi", "-t", str(silence_duration), "-i", "anullsrc=r=44100:cl=mono"])
            filter_parts.append(f"[{input_idx}:a]")
            input_idx += 1

    n_concat = len(filter_parts)
    filter_complex = "".join(filter_parts) + f"concat=n={n_concat}:v=0:a=1[out]"
    cmd.extend(["-filter_complex", filter_complex, "-map", "[out]",
                "-c:a", "libmp3lame", "-q:a", "2", str(output_path)])

    result = subprocess.run(cmd, capture_output=True, text=True, stdin=subprocess.DEVNULL)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg concat failed: {result.stderr}")
