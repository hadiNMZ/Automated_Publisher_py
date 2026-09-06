"""
Tracks used words per plugin (one JSON file per plugin, e.g.
trackers/german_used.json), so each language avoids repeating content
independently.
"""
import json
from datetime import date
from config_base import TRACKER_DIR


def _file_for(plugin_name: str):
    return TRACKER_DIR / f"{plugin_name}_used.json"


def load_used_words(plugin_name: str) -> list[str]:
    path = _file_for(plugin_name)
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return [entry["word"] for entry in data]


def record_word(plugin_name: str, phrase_data: dict) -> None:
    path = _file_for(plugin_name)
    entries = []
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            entries = json.load(f)

    entries.append({
        "date": str(date.today()),
        "word": phrase_data["word"],
        "level": phrase_data.get("level"),
    })

    with open(path, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)
