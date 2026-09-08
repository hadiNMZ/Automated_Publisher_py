"""
Multi-slide pipeline: builds 3 slides (Grammar, Word, Examples),
generates per-slide TTS audio, renders slides, crossfades them,
and publishes to Drive + YouTube.

Each slide's duration is calculated from its TTS audio length,
so the video pacing matches the narration naturally.
"""
import datetime
import json
import subprocess
from pathlib import Path

from tracker import load_used_words, record_word
from tts_registry import generate_audio_segments
from telegram_approval import send_audio_for_approval, send_video_for_approval, send_message
from render_backends import render
from upload_drive import upload_to_drive
from upload_youtube import upload_to_youtube

from language_common import get_intros


def _build_caption(plugin_name: str, phrase_data: dict) -> str:
    grammar = phrase_data.get("grammar", {})
    word = phrase_data.get("word", {})

    parts = [f"[{plugin_name.upper()}] {word.get('word', '?')} — {grammar.get('rule_name', '?')}"]

    parts.append(f"\n📖 GRAMMAR: {grammar.get('rule_name', '?')}")
    if grammar.get("rule_name_ar"):
        parts.append(f"   AR: {grammar['rule_name_ar']}")
    if grammar.get("explanation"):
        parts.append(f"   {grammar['explanation']}")
    if grammar.get("explanation_ar"):
        parts.append(f"   AR: {grammar['explanation_ar']}")
    parts.append(f"   5 examples")

    parts.append(f"\n📝 WORD: {word.get('word', '?')} ({word.get('level', '')})")
    if word.get("word_ar"):
        parts.append(f"   AR: {word['word_ar']}")
    if word.get("pronunciation"):
        parts.append(f"   pron: {word['pronunciation']}")
    parts.append(f"   Forms: noun(m/f), verb, informal — all with Arabic")

    parts.append(f"\n✅ 5 word examples with Arabic translations")

    return "\n".join(parts)


def _build_slide_1_grammar(phrase_data: dict, language_name: str, level: str) -> list[dict]:
    """Slide 1: Grammar rule + explanation + 5 examples."""
    grammar = phrase_data.get("grammar", {})
    plan = []

    plan.append({"type": "header", "text": f"{language_name} | {level}"})

    plan.append({"type": "section_header", "text": "Grammar Rule"})
    plan.append({"type": "main", "text": grammar.get("rule_name", "")})
    if grammar.get("rule_name_ar"):
        plan.append({"type": "arabic", "text": grammar["rule_name_ar"]})

    if grammar.get("explanation"):
        plan.append({"type": "label", "text": "(Explanation)"})
        plan.append({"type": "main", "text": grammar["explanation"]})
    if grammar.get("explanation_ar"):
        plan.append({"type": "arabic", "text": grammar["explanation_ar"]})

    plan.append({"type": "section_header", "text": "Examples"})
    for i, ex in enumerate(grammar.get("examples", [])):
        plan.append({"type": "translation", "text": f"{i+1}. {ex.get('sentence', '')}"})
        if ex.get("sentence_ar"):
            plan.append({"type": "arabic", "text": ex["sentence_ar"]})
        plan.append({"type": "example_gap", "text": ""})

    return plan


def _build_slide_2_word(phrase_data: dict, language_name: str, level: str) -> list[dict]:
    """Slide 2: Word of the day with all forms."""
    word = phrase_data.get("word", {})
    plan = []

    plan.append({"type": "header", "text": f"{language_name} | {level}"})

    plan.append({"type": "section_header", "text": "Word of the Day"})
    plan.append({"type": "main", "text": word.get("word", "")})
    if word.get("word_ar"):
        plan.append({"type": "arabic", "text": word["word_ar"]})

    if word.get("pronunciation"):
        plan.append({"type": "label", "text": "Pronunciation"})
        plan.append({"type": "main", "text": word["pronunciation"]})
    if word.get("pronunciation_ar"):
        plan.append({"type": "arabic", "text": word["pronunciation_ar"]})

    if word.get("noun_male"):
        plan.append({"type": "label", "text": "Noun (Male)"})
        plan.append({"type": "main", "text": word["noun_male"]})
    if word.get("noun_male_ar"):
        plan.append({"type": "arabic", "text": word["noun_male_ar"]})

    if word.get("noun_female"):
        plan.append({"type": "label", "text": "Noun (Female)"})
        plan.append({"type": "main", "text": word["noun_female"]})
    if word.get("noun_female_ar"):
        plan.append({"type": "arabic", "text": word["noun_female_ar"]})

    if word.get("verb_form"):
        plan.append({"type": "label", "text": "Verb"})
        plan.append({"type": "main", "text": word["verb_form"]})
    if word.get("verb_form_ar"):
        plan.append({"type": "arabic", "text": word["verb_form_ar"]})

    if word.get("informal"):
        plan.append({"type": "label", "text": "Informal"})
        plan.append({"type": "main", "text": word["informal"]})
    if word.get("informal_ar"):
        plan.append({"type": "arabic", "text": word["informal_ar"]})

    return plan


def _build_slide_3_examples(phrase_data: dict, language_name: str, level: str) -> list[dict]:
    """Slide 3: 5 word examples."""
    plan = []

    plan.append({"type": "header", "text": f"{language_name} | {level}"})

    plan.append({"type": "section_header", "text": "Examples"})

    for i, ex in enumerate(phrase_data.get("word_examples", [])):
        plan.append({"type": "translation", "text": f"{i+1}. {ex.get('sentence', '')}"})
        if ex.get("sentence_ar"):
            plan.append({"type": "arabic", "text": ex["sentence_ar"]})
        plan.append({"type": "example_gap", "text": ""})

    return plan


def _build_tts_segments_slide1(phrase_data: dict, target_lang: str) -> list[tuple[str, str]]:
    """TTS segments for Slide 1 (Grammar)."""
    grammar = phrase_data.get("grammar", {})
    intros = get_intros(target_lang)
    segments = []

    if grammar.get("rule_name"):
        segments.append((f"{intros['grammar']}: {grammar['rule_name']}.", target_lang))
    if grammar.get("rule_name_ar"):
        segments.append((grammar["rule_name_ar"], "ar"))

    if grammar.get("explanation"):
        segments.append((grammar["explanation"], target_lang))
    if grammar.get("explanation_ar"):
        segments.append((grammar["explanation_ar"], "ar"))

    if grammar.get("examples"):
        segments.append((f"{intros['examples']}.", target_lang))
        for i, ex in enumerate(grammar["examples"]):
            if ex.get("sentence"):
                segments.append((f"{i+1}. {ex['sentence']}", target_lang))
            if ex.get("sentence_ar"):
                segments.append((ex["sentence_ar"], "ar"))

    return segments


def _build_tts_segments_slide2(phrase_data: dict, target_lang: str) -> list[tuple[str, str]]:
    """TTS segments for Slide 2 (Word of the Day)."""
    word = phrase_data.get("word", {})
    intros = get_intros(target_lang)
    segments = []

    if word.get("word"):
        segments.append((f"{intros['word']}: {word['word']}.", target_lang))
    if word.get("word_ar"):
        segments.append((word["word_ar"], "ar"))

    if word.get("pronunciation"):
        segments.append((f"{intros['pronunciation']}: {word['pronunciation']}.", target_lang))

    fields = [
        ("noun_male", "noun_male_ar", "noun_male"),
        ("noun_female", "noun_female_ar", "noun_female"),
        ("verb_form", "verb_form_ar", "verb"),
        ("informal", "informal_ar", "informal"),
    ]
    for native_key, ar_key, intro_key in fields:
        if word.get(native_key):
            segments.append((f"{intros[intro_key]}: {word[native_key]}.", target_lang))
        if word.get(ar_key):
            segments.append((word[ar_key], "ar"))

    return segments


def _build_tts_segments_slide3(phrase_data: dict, target_lang: str) -> list[tuple[str, str]]:
    """TTS segments for Slide 3 (Word Examples)."""
    intros = get_intros(target_lang)
    segments = []

    segments.append((f"{intros['examples']}.", target_lang))
    for i, ex in enumerate(phrase_data.get("word_examples", [])):
        if ex.get("sentence"):
            segments.append((f"{i+1}. {ex['sentence']}", target_lang))
        if ex.get("sentence_ar"):
            segments.append((ex["sentence_ar"], "ar"))

    return segments


def _get_audio_duration(audio_path: Path) -> float:
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(audio_path)],
            capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=10
        )
        return float(result.stdout.strip())
    except Exception:
        return 10.0


def _concat_audio_files(audio_paths: list[Path], output_path: Path, silence_duration: float = 0.3) -> Path:
    """Concatenates audio files with silence between them."""
    cmd = ["ffmpeg", "-y"]
    filter_parts = []
    input_idx = 0

    for i, audio_path in enumerate(audio_paths):
        cmd.extend(["-i", str(audio_path)])
        filter_parts.append(f"[{input_idx}:a]")
        input_idx += 1
        if i < len(audio_paths) - 1:
            cmd.extend(["-f", "lavfi", "-t", str(silence_duration), "-i", "anullsrc=r=44100:cl=mono"])
            filter_parts.append(f"[{input_idx}:a]")
            input_idx += 1

    n_concat = len(filter_parts)
    filter_complex = "".join(filter_parts) + f"concat=n={n_concat}:v=0:a=1[out]"
    cmd.extend(["-filter_complex", filter_complex, "-map", "[out]",
                "-c:a", "libmp3lame", "-q:a", "2", str(output_path)])

    result = subprocess.run(cmd, capture_output=True, text=True, stdin=subprocess.DEVNULL)
    if result.returncode != 0:
        raise RuntimeError(f"Audio concat failed: {result.stderr}")
    return output_path


def run_plugin(plugin) -> None:
    """
    plugin must expose:
      - NAME, LANGUAGE_NAME: str
      - PENDING_DIR: Path
      - FONT_BOLD, FONT_REGULAR, FONT_ARABIC: str (paths)
      - generate_content(weekday, used_words) -> dict
      - TTS_PROVIDER: str, TTS_LANG_OR_VOICE: str
    """
    today = datetime.date.today().isoformat()
    day_dir = plugin.PENDING_DIR / today
    day_dir.mkdir(parents=True, exist_ok=True)

    try:
        print(f"[{plugin.NAME}] Generating content (3-slide montage)...")
        used = load_used_words(plugin.NAME)
        phrase_data = plugin.generate_content(datetime.date.today().weekday(), used)
        (day_dir / "phrase.json").write_text(
            json.dumps(phrase_data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        grammar = phrase_data.get("grammar", {})
        word = phrase_data.get("word", {})
        level = word.get("level", "A1")
        lang_name = plugin.LANGUAGE_NAME

        print(f"  -> Grammar: {grammar.get('rule_name', '?')}")
        print(f"  -> Word: {word.get('word', '?')}")
        print(f"  -> {len(grammar.get('examples', []))} grammar examples, {len(phrase_data.get('word_examples', []))} word examples")

        # Build 3 slide render plans
        slide1_plan = _build_slide_1_grammar(phrase_data, lang_name, level)
        slide2_plan = _build_slide_2_word(phrase_data, lang_name, level)
        slide3_plan = _build_slide_3_examples(phrase_data, lang_name, level)

        # Build per-slide TTS segments
        print(f"[{plugin.NAME}] Generating per-slide TTS...")
        slide1_segments = _build_tts_segments_slide1(phrase_data, plugin.TTS_LANG_OR_VOICE)
        slide2_segments = _build_tts_segments_slide2(phrase_data, plugin.TTS_LANG_OR_VOICE)
        slide3_segments = _build_tts_segments_slide3(phrase_data, plugin.TTS_LANG_OR_VOICE)

        print(f"  Slide 1: {len(slide1_segments)} segments")
        print(f"  Slide 2: {len(slide2_segments)} segments")
        print(f"  Slide 3: {len(slide3_segments)} segments")

        # Generate per-slide audio
        slide1_audio = day_dir / "audio_slide1.mp3"
        slide2_audio = day_dir / "audio_slide2.mp3"
        slide3_audio = day_dir / "audio_slide3.mp3"

        generate_audio_segments(plugin.TTS_PROVIDER, slide1_segments, plugin.TTS_LANG_OR_VOICE, slide1_audio)
        generate_audio_segments(plugin.TTS_PROVIDER, slide2_segments, plugin.TTS_LANG_OR_VOICE, slide2_audio)
        generate_audio_segments(plugin.TTS_PROVIDER, slide3_segments, plugin.TTS_LANG_OR_VOICE, slide3_audio)

        # Get per-slide durations
        dur1 = _get_audio_duration(slide1_audio)
        dur2 = _get_audio_duration(slide2_audio)
        dur3 = _get_audio_duration(slide3_audio)
        total_dur = dur1 + dur2 + dur3
        print(f"  Durations: slide1={dur1:.1f}s, slide2={dur2:.1f}s, slide3={dur3:.1f}s, total={total_dur:.1f}s")

        # Concatenate audio files
        full_audio = day_dir / "audio.mp3"
        _concat_audio_files([slide1_audio, slide2_audio, slide3_audio], full_audio)

        caption = _build_caption(plugin.NAME, phrase_data)

        print(f"[{plugin.NAME}] Sending audio for approval...")
        if not send_audio_for_approval(full_audio, caption):
            print(f"[{plugin.NAME}] Denied at audio stage. Stopping.")
            return

        # Build slides list for renderer
        slides = [
            {"render_plan": slide1_plan, "duration": dur1},
            {"render_plan": slide2_plan, "duration": dur2},
            {"render_plan": slide3_plan, "duration": dur3},
        ]

        print(f"[{plugin.NAME}] Rendering 3-slide video with crossfade...")
        video_path = render(slides, full_audio, day_dir / "output.mp4",
                            plugin.FONT_BOLD, plugin.FONT_REGULAR, plugin.FONT_ARABIC, total_dur)

        print(f"[{plugin.NAME}] Sending video for approval...")
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
