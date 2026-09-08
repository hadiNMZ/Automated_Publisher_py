"""
Shared prompt template for the 3-slide montage format.

Produces a JSON structure with:
  - grammar: rule name + explanation + 5 examples (all with Arabic translations)
  - word: word + pronunciation + noun male/female + verb form + informal (all with Arabic)
  - word_examples: 5 example sentences using the word (with Arabic translations)

ALL content is in the target language + Arabic only. No English translations.
The only English used is the phonetic pronunciation guide (plain English letters).
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

# Intro phrases per language — used by TTS to announce sections in the target language
INTROS = {
    "de": {"grammar": "Grammatik", "word": "Wort des Tages", "example": "Beispiel", "examples": "Beispiele", "usage": "Verwendung", "meaning": "Bedeutung", "pronunciation": "Aussprache", "noun_male": "Substantiv maskulin", "noun_female": "Substantiv feminin", "verb": "Verb", "informal": "Umgangssprachlich"},
    "fr": {"grammar": "Grammaire", "word": "Mot du jour", "example": "Exemple", "examples": "Exemples", "usage": "Usage", "meaning": "Signification", "pronunciation": "Prononciation", "noun_male": "Nom masculin", "noun_female": "Nom féminin", "verb": "Verbe", "informal": "Familier"},
    "es": {"grammar": "Gramática", "word": "Palabra del día", "example": "Ejemplo", "examples": "Ejemplos", "usage": "Uso", "meaning": "Significado", "pronunciation": "Pronunciación", "noun_male": "Sustantivo masculino", "noun_female": "Sustantivo femenino", "verb": "Verbo", "informal": "Informal"},
    "en": {"grammar": "Grammar", "word": "Word of the day", "example": "Example", "examples": "Examples", "usage": "Usage", "meaning": "Meaning", "pronunciation": "Pronunciation", "noun_male": "Noun (male)", "noun_female": "Noun (female)", "verb": "Verb", "informal": "Informal"},
    "cs": {"grammar": "Gramatika", "word": "Slovo dne", "example": "Příklad", "examples": "Příklady", "usage": "Použití", "meaning": "Význam", "pronunciation": "Výslovnost", "noun_male": "Podstatné jméno (mužské)", "noun_female": "Podstatné jméno (ženské)", "verb": "Sloveso", "informal": "Neformální"},
}


def build_prompt(
    language_name: str,
    theme: str,
    used_words: list[str],
    include_english: bool,  # ignored — kept for backwards compat
    include_arabic: bool,   # always True in the new schema
) -> str:
    used_list = "\n".join(f"- {w}" for w in used_words[-30:]) or "(none yet)"

    return f"""You are a {language_name} language teacher creating content for a
YouTube Shorts series aimed at Arabic-speaking beginners (A1-A2 level).

Today's theme: {theme}

Generate ONE educational segment with THREE parts. ALL content must be in
{language_name} with Arabic translations. Do NOT include any English
translations — only {language_name} and Arabic.

PART 1 — GRAMMAR:
  - rule_name: the grammar rule name in {language_name}
  - rule_name_ar: Arabic translation of the rule name
  - explanation: 1-2 sentence explanation of the rule in {language_name}
  - explanation_ar: Arabic translation of the explanation
  - examples: array of 5 example sentences demonstrating this grammar rule.
    Each example has:
    - sentence: the sentence in {language_name}
    - sentence_ar: Arabic translation of the sentence

PART 2 — WORD OF THE DAY:
  A word or short phrase related to today's theme. Include ALL of these
  fields even if some don't apply perfectly (use "N/A" if truly not
  applicable, but try to fill them all):
  - word: the word in {language_name}
  - word_ar: Arabic translation of the word
  - pronunciation: phonetic guide using plain English letters only (e.g.
    "ap-fl" for "Apfel"). No IPA. Hyphenate between syllables.
  - pronunciation_ar: Arabic phonetic approximation of how to pronounce it
  - noun_male: the masculine noun form in {language_name} (or related noun)
  - noun_male_ar: Arabic translation
  - noun_female: the feminine noun form in {language_name} (or related noun)
  - noun_female_ar: Arabic translation
  - verb_form: a verb form related to this word in {language_name}
  - verb_form_ar: Arabic translation
  - informal: an informal/colloquial version in {language_name}
  - informal_ar: Arabic translation
  - level: "A1" or "A2"

PART 3 — WORD EXAMPLES:
  5 example sentences that use the WORD from Part 2 (NOT the same as the
  grammar examples in Part 1). These show the word used in context.
  Each example has:
  - sentence: the sentence in {language_name}
  - sentence_ar: Arabic translation of the sentence

Do NOT reuse any of these already-used words:
{used_list}

Respond ONLY with valid JSON in this exact structure, no markdown, no commentary:

{{
  "grammar": {{
    "rule_name": "...",
    "rule_name_ar": "...",
    "explanation": "...",
    "explanation_ar": "...",
    "examples": [
      {{"sentence": "...", "sentence_ar": "..."}},
      {{"sentence": "...", "sentence_ar": "..."}},
      {{"sentence": "...", "sentence_ar": "..."}},
      {{"sentence": "...", "sentence_ar": "..."}},
      {{"sentence": "...", "sentence_ar": "..."}}
    ]
  }},
  "word": {{
    "word": "...",
    "word_ar": "...",
    "pronunciation": "...",
    "pronunciation_ar": "...",
    "noun_male": "...",
    "noun_male_ar": "...",
    "noun_female": "...",
    "noun_female_ar": "...",
    "verb_form": "...",
    "verb_form_ar": "...",
    "informal": "...",
    "informal_ar": "...",
    "level": "A1"
  }},
  "word_examples": [
    {{"sentence": "...", "sentence_ar": "..."}},
    {{"sentence": "...", "sentence_ar": "..."}},
    {{"sentence": "...", "sentence_ar": "..."}},
    {{"sentence": "...", "sentence_ar": "..."}},
    {{"sentence": "...", "sentence_ar": "..."}}
  ]
}}
"""


def extract_json(text: str) -> dict:
    """Models often wrap JSON in ```json fences despite instructions — strip them."""
    cleaned = re.sub(r"```json|```", "", text).strip()
    return json.loads(cleaned)


def get_theme(weekday: int) -> str:
    return THEMES_BY_WEEKDAY.get(weekday, "everyday life")


def get_intros(lang_code: str) -> dict:
    """Returns the intro phrases for a given language code."""
    return INTROS.get(lang_code, INTROS["en"])
