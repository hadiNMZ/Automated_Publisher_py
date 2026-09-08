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

    # Defensive: older versions stored the whole word dict instead of the
    # word string — normalize both shapes to a plain string list.
    words = []
    for entry in data:
        w = entry.get("word")
        if isinstance(w, dict):
            w = w.get("word")
        if w:
            words.append(w)
    return words


def record_word(plugin_name: str, phrase_data: dict) -> None:
    path = _file_for(plugin_name)
    entries = []
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            entries = json.load(f)

    # phrase_data["word"] is the word OBJECT ({"word": ..., "level": ...,
    # ...}) — store the word STRING and its level, matching the tracker
    # file format and keeping load_used_words() returning plain strings.
    word_obj = phrase_data.get("word", {})
    if isinstance(word_obj, dict):
        word_str = word_obj.get("word", "")
        level = word_obj.get("level")
    else:
        word_str = word_obj
        level = phrase_data.get("level")

    entries.append({
        "date": str(date.today()),
        "word": word_str,
        "level": level,
    })

    with open(path, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)
