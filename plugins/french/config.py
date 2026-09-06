"""French plugin: target language French, translated to English + Arabic."""
from pathlib import Path
import sys

PLUGIN_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(PLUGIN_DIR.parent.parent / "core"))

from phrase_providers import generate_phrase
from language_common import get_theme

NAME = "french"
LANGUAGE_NAME = "French"
INCLUDE_ENGLISH = True
INCLUDE_ARABIC = True

TTS_PROVIDER = "google"
TTS_LANG_OR_VOICE = "fr"

PENDING_DIR = PLUGIN_DIR / "pending"
PUBLISHED_DIR = PLUGIN_DIR / "published"
PENDING_DIR.mkdir(exist_ok=True)
PUBLISHED_DIR.mkdir(exist_ok=True)

FONT_BOLD = str(PLUGIN_DIR / "assets" / "Inter-Bold.ttf")
FONT_REGULAR = str(PLUGIN_DIR / "assets" / "Inter-Regular.ttf")


def generate_content(weekday: int, used_words: list[str]) -> dict:
    theme = get_theme(weekday)
    return generate_phrase(LANGUAGE_NAME, weekday, theme, used_words,
                            INCLUDE_ENGLISH, INCLUDE_ARABIC)
