"""
ElevenLabs TTS. lang_or_voice here is an ElevenLabs voice ID (voice
choice determines the language/accent, not a separate lang parameter).
"""
import requests
from pathlib import Path
from config_base import ELEVENLABS_API_KEY

URL_TEMPLATE = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"


def generate(text: str, lang_or_voice: str, output_path: Path) -> Path:
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
