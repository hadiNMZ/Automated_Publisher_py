"""
TTS dispatcher with multilingual segment support.

Task 1b update: adds generate_audio_segments() for multilingual TTS.
Each segment is a (text, lang_code) tuple — the provider generates
audio for each segment in the correct language, then concatenates
them into a single file.

This fixes the "English text read in a German accent" problem: now
English segments are read in English, Arabic segments in Arabic, and
target-language segments in the target language — all in one audio file.

Task 3 update:
  - Adds "edge" provider (Microsoft Edge neural voices — free, much
    better pronunciation than gTTS, natural Arabic support).
  - Every segment is now sanitized through sanitize_for_tts() before
    hitting any provider, so quote/bracket/paren characters are never
    read aloud ("open bracket", "quote", "علامة تنصيص", ...).

Providers implement TWO functions:
  - generate(text, lang_or_voice, output_path)           — old single-text interface
  - generate_segments(segments, lang_or_voice, output_path) — new multilingual interface

The pipeline calls generate_segments(). The old generate() is kept for
backwards compatibility and standalone testing.
"""
from pathlib import Path
from tts_providers import google_tts, elevenlabs_tts, kokoro_tts, edge_tts
from tts_providers.common import sanitize_for_tts

PROVIDERS = {
    "google": google_tts,
    "elevenlabs": elevenlabs_tts,
    "kokoro": kokoro_tts,
    "edge": edge_tts,
}


def generate_audio(provider: str, text: str, lang_or_voice: str, output_path: Path) -> Path:
    """Old single-text interface — kept for backwards compat and testing."""
    mod = PROVIDERS.get(provider)
    if mod is None:
        raise ValueError(f"Unknown TTS provider '{provider}' — available: {list(PROVIDERS)}")
    return mod.generate(sanitize_for_tts(text), lang_or_voice, output_path)


def generate_audio_segments(
    provider: str,
    segments: list[tuple[str, str]],
    lang_or_voice: str,
    output_path: Path,
) -> Path:
    """
    Multilingual TTS: generates audio for each (text, lang_code) segment
    in the correct language, then concatenates them into a single file.

    segments: list of (text, lang_code) tuples, e.g.
        [("Grammatik:", "de"), ("The accusative case...", "en"), ("التفاحة", "ar")]
    lang_or_voice: the plugin's TTS_LANG_OR_VOICE value. For edge/google
        this relates to the target language (per-segment languages are
        resolved individually). For ElevenLabs this is the voice ID.
        For Kokoro this is the voice name (English-only provider).
    output_path: where to write the final combined audio file.
    """
    mod = PROVIDERS.get(provider)
    if mod is None:
        raise ValueError(f"Unknown TTS provider '{provider}' — available: {list(PROVIDERS)}")

    # Strip characters TTS engines read aloud (quotes, brackets, parens...)
    segments = [(sanitize_for_tts(text), lang) for text, lang in segments]

    return mod.generate_segments(segments, lang_or_voice, output_path)
