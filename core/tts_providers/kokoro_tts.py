"""
Kokoro local TTS server. English-only in practice (Kokoro-82M has no
German/French/Spanish support) — kept here for the English plugin, or
future English-language niches (gaming/streamer clips).
"""
import requests
from pathlib import Path
from config_base import KOKORO_API_URL


def generate(text: str, lang_or_voice: str, output_path: Path) -> Path:
    payload = {"model": "kokoro", "input": text, "voice": lang_or_voice, "response_format": "mp3"}
    resp = requests.post(KOKORO_API_URL, json=payload, timeout=60)
    resp.raise_for_status()
    output_path.write_bytes(resp.content)
    return output_path
