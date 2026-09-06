"""
Dispatcher for TTS. Unlike the old single-language project, the
provider AND the voice/lang code are passed in per-call — each plugin's
config declares its own (provider, voice_or_lang) pair, so German,
French, Spanish, and English can each use a different provider/voice.

To add a new TTS provider: drop a new module in tts_providers/ with a
generate(text, lang_or_voice, output_path) function, then register it
in PROVIDERS below.
"""
from pathlib import Path
from tts_providers import google_tts, elevenlabs_tts, kokoro_tts

PROVIDERS = {
    "google": google_tts.generate,
    "elevenlabs": elevenlabs_tts.generate,
    "kokoro": kokoro_tts.generate,
    # "your_new_provider": your_new_provider.generate,
}


def generate_audio(provider: str, text: str, lang_or_voice: str, output_path: Path) -> Path:
    fn = PROVIDERS.get(provider)
    if fn is None:
        raise ValueError(f"Unknown TTS provider '{provider}' — available: {list(PROVIDERS)}")
    return fn(text, lang_or_voice, output_path)
