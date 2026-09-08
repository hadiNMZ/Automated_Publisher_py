"""
ElevenLabs TTS with multilingual segment support.

Task 1b update: adds generate_segments(). ElevenLabs has multilingual
voices (eleven_multilingual_v2 model) that can handle mixed languages
in a single call, so segments are joined into one text block and
generated in a single API call.

This is more efficient than calling the API per segment (saves API
quota), and ElevenLabs handles language switching naturally within
the multilingual model.
"""
import requests
from pathlib import Path
from config_base import ELEVENLABS_API_KEY

URL_TEMPLATE = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"


def generate(text: str, lang_or_voice: str, output_path: Path) -> Path:
    """Old single-text interface."""
    url = URL_TEMPLATE.format(voice_id=lang_or_voice)
    headers = {"xi-api-key": ELEVENLABS_API_KEY, "Content-Type": "application/json"}
    payload = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {"stability": 0.6, "similarity_boost": 0.8},
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=60)
    resp.raise_for_status()
    output_path.write_bytes(resp.content)
    return output_path


def generate_segments(
    segments: list[tuple[str, str]],
    lang_or_voice: str,
    output_path: Path,
) -> Path:
    """
    ElevenLabs multilingual: joins all segments into one text block
    (separated by newlines) and generates in a single API call using
    the eleven_multilingual_v2 model, which handles language switching
    automatically based on the text content.

    lang_or_voice: the ElevenLabs voice ID to use.
    """
    # Join all segment texts with line breaks — ElevenLabs multilingual
    # model detects language from the text itself
    full_text = "\n".join(text for text, _ in segments if text and text.strip())

    if not full_text.strip():
        raise ValueError("No non-empty TTS segments provided")

    return generate(full_text, lang_or_voice, output_path)
