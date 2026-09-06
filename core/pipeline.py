"""
Generic pipeline: generate content -> TTS -> Telegram approve/deny ->
render -> Telegram approve/deny -> Drive -> YouTube.

Every plugin (german, french, spanish, english, and later gaming/
streamer_clips/anime) runs through this exact same function — only the
plugin's own config and generate_content() differ.
"""
import datetime
import json
from pathlib import Path

from tracker import load_used_words, record_word
from tts_registry import generate_audio
from telegram_approval import send_audio_for_approval, send_video_for_approval, send_message
from render_backends import render
from upload_drive import upload_to_drive
from upload_youtube import upload_to_youtube


def _build_caption(plugin_name: str, phrase_data: dict) -> str:
    parts = [f"[{plugin_name.upper()}] {phrase_data['word']} ({phrase_data.get('category', '')})"]
    if "translation_en" in phrase_data:
        parts.append(f"EN: {phrase_data['translation_en']}")
    if "translation_ar" in phrase_data:
        parts.append(f"AR: {phrase_data['translation_ar']}")
    if "example_native" in phrase_data:
        parts.append(f"Example: {phrase_data['example_native']}")
    if "example_en" in phrase_data:
        parts.append(f"  ({phrase_data['example_en']})")
    if "example_ar" in phrase_data:
        parts.append(f"  ({phrase_data['example_ar']})")
    parts.append(f"Level: {phrase_data.get('level', '')}")
    return "\n".join(parts)


def _build_text_lines(phrase_data: dict) -> list[str]:
    lines = [phrase_data["word"]]
    if "translation_en" in phrase_data:
        lines.append(phrase_data["translation_en"])
    if "translation_ar" in phrase_data:
        lines.append(phrase_data["translation_ar"])
    lines.append(phrase_data.get("example_native", ""))
    return lines


def run_plugin(plugin) -> None:
    """
    plugin must expose:
      - NAME: str
      - PENDING_DIR: Path
      - FONT_BOLD, FONT_REGULAR: str (paths)
      - generate_content(weekday, used_words) -> dict
      - TTS_PROVIDER: str, TTS_LANG_OR_VOICE: str
    """
    today = datetime.date.today().isoformat()
    day_dir = plugin.PENDING_DIR / today
    day_dir.mkdir(parents=True, exist_ok=True)

    try:
        print(f"[{plugin.NAME}] Generating today's word...")
        used = load_used_words(plugin.NAME)
        phrase_data = plugin.generate_content(datetime.date.today().weekday(), used)
        (day_dir / "phrase.json").write_text(
            json.dumps(phrase_data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"  -> {phrase_data['word']} ({phrase_data.get('category')})")

        print(f"[{plugin.NAME}] Generating audio...")
        tts_text = phrase_data["word"] + ". ... " + phrase_data.get("example_native", "")
        audio_path = generate_audio(plugin.TTS_PROVIDER, tts_text, plugin.TTS_LANG_OR_VOICE,
                                     day_dir / "audio.mp3")

        caption = _build_caption(plugin.NAME, phrase_data)

        print(f"[{plugin.NAME}] Sending audio for approval — waiting for your response...")
        if not send_audio_for_approval(audio_path, caption):
            print(f"[{plugin.NAME}] Denied at audio stage. Stopping.")
            return

        print(f"[{plugin.NAME}] Rendering video...")
        text_lines = _build_text_lines(phrase_data)
        video_path = render(text_lines, audio_path, day_dir / "output.mp4",
                             plugin.FONT_BOLD, plugin.FONT_REGULAR)

        print(f"[{plugin.NAME}] Sending video for approval — waiting for your response...")
        if not send_video_for_approval(video_path, caption):
            print(f"[{plugin.NAME}] Denied at video stage. Stopping.")
            return

        print(f"[{plugin.NAME}] Uploading to Drive...")
        drive_id = upload_to_drive(video_path, plugin.NAME, phrase_data)

        print(f"[{plugin.NAME}] Uploading to YouTube...")
        youtube_id = upload_to_youtube(video_path, plugin.NAME, phrase_data)

        record_word(plugin.NAME, phrase_data)

        send_message(f"✅ [{plugin.NAME}] Published: https://youtube.com/watch?v={youtube_id}")
        print(f"[{plugin.NAME}] Done. https://youtube.com/watch?v={youtube_id}")

    except Exception as e:
        send_message(f"⚠️ [{plugin.NAME}] pipeline failed: {e}")
        raise
