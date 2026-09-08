"""
Post-processes generated audio to adjust playback speed via ffmpeg's
atempo filter. This runs AFTER whichever TTS provider generated the
audio (gTTS, ElevenLabs, Kokoro) so speed control works the same way
regardless of provider -- most providers don't offer fine-grained
speed control natively (gTTS only has a blunt slow=True/False flag).
"""
import subprocess
from pathlib import Path
from config_base import FFMPEG_BINARY, TTS_SPEED


def _run_ffmpeg(cmd: list[str]) -> None:
    result = subprocess.run(cmd, capture_output=True, text=True, stdin=subprocess.DEVNULL)
    if result.returncode != 0:
        raise RuntimeError(
            f"ffmpeg failed (exit {result.returncode}) adjusting audio speed.\n"
            f"Command: {' '.join(cmd)}\n\nffmpeg stderr:\n{result.stderr}"
        )


def adjust_speed(audio_path: Path, tempo: float = None) -> Path:
    """
    Slows down (tempo < 1.0) or speeds up (tempo > 1.0) an audio file
    IN PLACE (overwrites audio_path with the adjusted version), using
    ffmpeg's atempo filter. atempo only accepts values from 0.5 to 2.0
    per instance -- plenty of range for slowing down speech.

    Pass tempo explicitly to override the .env default for one call
    (e.g. a plugin doing full-sentence grammar explanations might want
    it slower than a single vocabulary word).
    """
    tempo = TTS_SPEED if tempo is None else tempo

    if tempo == 1.0:
        return audio_path  # no-op, skip re-encoding entirely

    if not (0.5 <= tempo <= 2.0):
        raise ValueError(f"atempo only supports 0.5-2.0, got {tempo}")

    temp_output = audio_path.with_name(audio_path.stem + "_speedtmp" + audio_path.suffix)
    _run_ffmpeg([
        FFMPEG_BINARY, "-y",
        "-i", str(audio_path),
        "-filter:a", f"atempo={tempo}",
        str(temp_output),
    ])
    temp_output.replace(audio_path)
    return audio_path
