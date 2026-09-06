"""
gTTS-based TTS. lang_or_voice here is a gTTS language code (e.g. "de",
"fr", "es", "en").
"""
from pathlib import Path
from gtts import gTTS


def generate(text: str, lang_or_voice: str, output_path: Path) -> Path:
    tts = gTTS(text=text, lang=lang_or_voice)
    tts.save(str(output_path))
    return output_path
