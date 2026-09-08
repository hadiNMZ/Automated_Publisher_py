"""
Publishes a 3-slide montage video to YouTube.
Metadata includes grammar rule, word with all forms, and examples.
"""
from pathlib import Path
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth import get_youtube_credentials
from config_base import YOUTUBE_CATEGORY_ID


def _build_metadata(plugin_name: str, phrase_data: dict) -> dict:
    grammar = phrase_data.get("grammar", {})
    word = phrase_data.get("word", {})

    word_str = word.get("word", "")
    rule = grammar.get("rule_name", "")
    level = word.get("level", "A1")

    title = f"{plugin_name.capitalize()} Word of the Day: {word_str} | Grammar: {rule}"
    if len(title) > 100:
        title = title[:97] + "..."

    lines = []

    lines.append("📖 GRAMMAR")
    if rule:
        lines.append(f"Rule: {rule}")
    if grammar.get("rule_name_ar"):
        lines.append(f"القاعدة: {grammar['rule_name_ar']}")
    if grammar.get("explanation"):
        lines.append(f"Explanation: {grammar['explanation']}")
    if grammar.get("explanation_ar"):
        lines.append(f"الشرح: {grammar['explanation_ar']}")
    lines.append(f"\n5 grammar examples with Arabic translations")

    lines.append("\n📝 WORD OF THE DAY")
    lines.append(f"Word: {word_str}")
    if word.get("word_ar"):
        lines.append(f"الكلمة: {word['word_ar']}")
    if word.get("pronunciation"):
        lines.append(f"Pronunciation: {word['pronunciation']}")
    if word.get("noun_male"):
        lines.append(f"Noun (M): {word['noun_male']} — {word.get('noun_male_ar', '')}")
    if word.get("noun_female"):
        lines.append(f"Noun (F): {word['noun_female']} — {word.get('noun_female_ar', '')}")
    if word.get("verb_form"):
        lines.append(f"Verb: {word['verb_form']} — {word.get('verb_form_ar', '')}")
    if word.get("informal"):
        lines.append(f"Informal: {word['informal']} — {word.get('informal_ar', '')}")

    lines.append(f"\n✅ 5 word examples with Arabic translations")

    lines.append(f"\nLearn {plugin_name.capitalize()} one word and one grammar rule at a time!")
    lines.append(f"#{plugin_name}wordoftheday #learn{plugin_name} #{level} #grammar #arabic")

    tags = [f"learn {plugin_name}", f"{plugin_name} grammar", level, "arabic translation"]

    return {
        "snippet": {"title": title, "description": "\n".join(lines), "tags": tags,
                    "categoryId": YOUTUBE_CATEGORY_ID},
        "status": {"privacyStatus": "public"},
    }


def upload_to_youtube(video_path: Path, plugin_name: str, phrase_data: dict) -> str:
    creds = get_youtube_credentials()
    service = build("youtube", "v3", credentials=creds)

    body = _build_metadata(plugin_name, phrase_data)
    media = MediaFileUpload(str(video_path), mimetype="video/mp4", resumable=True)
    request = service.videos().insert(part="snippet,status", body=body, media_body=media)

    response = None
    while response is None:
        status, response = request.next_chunk()

    return response.get("id")
