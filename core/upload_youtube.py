"""
Publishes a video to YouTube. Metadata is built generically from
whatever translation fields the phrase_data actually has (English
and/or Arabic), so it works for every language plugin without changes.
"""
from pathlib import Path
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth import get_youtube_credentials
from config_base import YOUTUBE_CATEGORY_ID


def _build_metadata(plugin_name: str, phrase_data: dict) -> dict:
    word = phrase_data["word"]
    level = phrase_data.get("level", "")
    category = phrase_data.get("category", "")

    lines = []
    if "translation_en" in phrase_data:
        lines.append(f"English: {phrase_data['translation_en']}")
    if "translation_ar" in phrase_data:
        lines.append(f"Arabic: {phrase_data['translation_ar']}")
    if "example_native" in phrase_data:
        lines.append(f"Example: {phrase_data['example_native']}")
    if "example_en" in phrase_data:
        lines.append(f"  ({phrase_data['example_en']})")
    if "example_ar" in phrase_data:
        lines.append(f"  ({phrase_data['example_ar']})")
    if "tip" in phrase_data:
        lines.append(f"Tip: {phrase_data['tip']}")

    title = f"{plugin_name.capitalize()} Word of the Day: {word}"
    description = "\n".join(lines) + f"\n\n#{plugin_name}wordoftheday #learn{plugin_name} #{level}"
    tags = [f"learn {plugin_name}", f"{plugin_name} word of the day", category, level]

    return {
        "snippet": {"title": title, "description": description, "tags": tags,
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
