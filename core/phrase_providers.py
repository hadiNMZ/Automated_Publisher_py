"""
Dispatcher for phrase-text generation. Shared across every language
plugin — each plugin just supplies the language name, theme, used-words
list, and translation flags; this module handles which model actually
answers (LM Studio locally, or Gemini).
"""
from config_base import PHRASE_PROVIDER, GEMINI_API_KEY, LMSTUDIO_API_URL, LMSTUDIO_MODEL
from language_common import build_prompt, extract_json
import requests


def _call_lmstudio(prompt: str) -> str:
    payload = {
        "model": LMSTUDIO_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.8,
    }
    resp = requests.post(LMSTUDIO_API_URL, json=payload, timeout=120)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def _call_gemini(prompt: str) -> str:
    try:
        import google.generativeai as genai
    except ImportError as e:
        raise RuntimeError(
            "google-generativeai isn't installed. Either install it, "
            "or set PHRASE_PROVIDER=lmstudio in .env."
        ) from e
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-2.0-flash")
    response = model.generate_content(prompt)
    return response.text


def generate_phrase(
    language_name: str,
    weekday: int,
    theme: str,
    used_words: list[str],
    include_english: bool,
    include_arabic: bool,
) -> dict:
    prompt = build_prompt(language_name, theme, used_words, include_english, include_arabic)

    if PHRASE_PROVIDER == "lmstudio":
        raw_text = _call_lmstudio(prompt)
    elif PHRASE_PROVIDER == "gemini":
        raw_text = _call_gemini(prompt)
    else:
        raise ValueError(f"Unknown PHRASE_PROVIDER '{PHRASE_PROVIDER}'")

    return extract_json(raw_text)
