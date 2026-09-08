"""
Microsoft Edge TTS provider — free, high-quality neural voices.

Why this provider:
  - Dramatically better pronunciation than gTTS (true neural voices,
    natural intonation — the fix for "pronunciation isn't the best")
  - Multilingual out of the box, including well-supported Arabic
    (gTTS Arabic is robotic; Edge ar-SA voices sound natural)
  - Free (no API key), uses the Edge Read Aloud service
  - Requires internet, same as gTTS

Voices are configured per plugin via TTS_LANG_OR_VOICE (a full voice
name like "de-DE-KatjaNeural"). Segments in OTHER languages (English
explanations, Arabic translations) are resolved through EDGE_VOICE_MAP
in config_base.py (overridable via EDGE_VOICE_* in .env).

Popular voices:
  de  de-DE-KatjaNeural (f) / de-DE-ConradNeural (m)
  fr  fr-FR-DeniseNeural (f) / fr-FR-HenriNeural (m)
  es  es-ES-ElviraNeural (f) / es-ES-AlvaroNeural (m)
  en  en-US-AvaMultilingualNeural (f) / en-US-BrianMultilingualNeural (m)
  ar  ar-SA-ZariyahNeural (f) / ar-SA-HamedNeural (m)

Browse the full list:  edge-tts --list-voices
"""
import asyncio
from pathlib import Path

import edge_tts

from config_base import EDGE_VOICE_MAP
from .common import concat_with_silence


def _resolve_voice(lang_code: str, plugin_voice: str) -> str:
    """
    Picks the voice for one segment.

    - If the segment's language IS the plugin's target language, use the
      plugin's configured voice (TTS_LANG_OR_VOICE, e.g. "de-DE-KatjaNeural").
    - Otherwise (English explanation, Arabic translation) use EDGE_VOICE_MAP.
    - If the plugin passed a bare language code ("de") instead of a full
      voice name, resolve everything through EDGE_VOICE_MAP.
    """
    lang_code = (lang_code or "").lower()
    plugin_voice = plugin_voice or ""
    is_full_voice = "-" in plugin_voice
    if is_full_voice:
        target_lang = plugin_voice.split("-")[0].lower()
        if lang_code == target_lang:
            return plugin_voice
        return EDGE_VOICE_MAP.get(lang_code, plugin_voice)
    # Bare lang code mode: map everything
    return EDGE_VOICE_MAP.get(lang_code, EDGE_VOICE_MAP.get(plugin_voice.lower(), plugin_voice))


async def _synth(text: str, voice: str, output_path: Path) -> None:
    await edge_tts.Communicate(text, voice).save(str(output_path))


def generate(text: str, lang_or_voice: str, output_path: Path) -> Path:
    """Old single-text interface. Accepts a full voice name or a lang code."""
    voice = _resolve_voice("", lang_or_voice)
    asyncio.run(_synth(text, voice, output_path))
    return output_path


def generate_segments(
    segments: list[tuple[str, str]],
    lang_or_voice: str,
    output_path: Path,
) -> Path:
    """
    Multilingual TTS: each (text, lang) segment is synthesized with the
    voice for ITS language (plugin voice for the target language,
    EDGE_VOICE_MAP for English/Arabic side content), then all segments
    are concatenated with 0.3s silence between them.
    """
    segments = [(text, lang) for text, lang in segments if text and text.strip()]
    if not segments:
        raise ValueError("No non-empty TTS segments provided")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    temp_files = []
    for i, (text, lang) in enumerate(segments):
        voice = _resolve_voice(lang, lang_or_voice)
        temp_path = output_path.parent / f"_tts_segment_{i}.mp3"
        try:
            asyncio.run(_synth(text, voice, temp_path))
            temp_files.append(temp_path)
        except Exception as e:
            # Skip a failing segment rather than killing the whole pipeline
            print(f"  [edge_tts] WARNING: segment {i} (voice={voice}) failed: {e}")
            if temp_path.exists():
                temp_path.unlink()

    if not temp_files:
        raise RuntimeError("All Edge TTS segments failed to generate")

    if len(temp_files) == 1:
        import shutil
        shutil.copy(str(temp_files[0]), str(output_path))
        temp_files[0].unlink()
        return output_path

    concat_with_silence(temp_files, output_path, silence_duration=0.3)

    for tf in temp_files:
        if tf.exists():
            tf.unlink()

    return output_path
