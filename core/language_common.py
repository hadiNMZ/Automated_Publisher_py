"""
Shared prompt template and JSON parsing used by every language plugin
(German, French, Spanish, English). A plugin's config.py declares which
translations it needs (English/Arabic) and this module builds the right
prompt and validates the right fields accordingly.
"""
import json
import re

THEMES_BY_WEEKDAY = {
    0: "greetings and introductions",
    1: "food and ordering at a restaurant",
    2: "travel and directions",
    3: "small talk and weather",
    4: "shopping and numbers",
    5: "hobbies and free time",
    6: "common idioms",
}


def build_prompt(
    language_name: str,
    theme: str,
    used_words: list[str],
    include_english: bool,
    include_arabic: bool,
) -> str:
    used_list = "\n".join(f"- {w}" for w in used_words[-30:]) or "(none yet)"

    fields = ['  "word": "the word or short phrase in ' + language_name + '"']
    if include_english:
        fields.append('  "translation_en": "English translation"')
    if include_arabic:
        fields.append('  "translation_ar": "Arabic translation"')
    fields.append('  "category": "verb" or "noun" or "vocabulary"')
    fields.append('  "example_native": "a short example sentence in ' + language_name + '"')
    if include_english:
        fields.append('  "example_en": "English translation of the example sentence"')
    if include_arabic:
        fields.append('  "example_ar": "Arabic translation of the example sentence"')
    fields.append('  "level": "A1 or A2"')
    fields.append('  "tip": "one short grammar or cultural note, max 15 words"')

    fields_block = ",\n".join(fields)

    return f"""You are a {language_name} language teacher creating content for a
YouTube Shorts series aimed at beginners (A1-A2 level).

Generate ONE new {language_name} word or short phrase for today's theme: {theme}

Also classify its grammatical category as exactly one of: verb, noun, vocabulary
(use "vocabulary" for anything that isn't clearly a single verb or noun — set
phrases, adjectives, adverbs, etc).

Do NOT reuse any of these already-used words:
{used_list}

Respond ONLY with valid JSON in this exact structure, no markdown, no commentary:

{{
{fields_block}
}}
"""


def extract_json(text: str) -> dict:
    """Models often wrap JSON in ```json fences despite instructions — strip them."""
    cleaned = re.sub(r"```json|```", "", text).strip()
    return json.loads(cleaned)


def get_theme(weekday: int) -> str:
    return THEMES_BY_WEEKDAY.get(weekday, "everyday life")
