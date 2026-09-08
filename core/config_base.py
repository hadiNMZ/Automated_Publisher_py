"""
Shared configuration for the whole monorepo — every plugin reads from
this for credentials and shared paths. Plugin-specific settings (which
language, which TTS voice, etc.) live in each plugin's own config.py.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# --- Phrase-generation provider: "gemini" | "lmstudio" ---
PHRASE_PROVIDER = os.getenv("PHRASE_PROVIDER", "lmstudio")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
LMSTUDIO_API_URL = os.getenv("LMSTUDIO_API_URL", "http://127.0.0.1:1234/v1/chat/completions")
LMSTUDIO_MODEL = os.getenv("LMSTUDIO_MODEL", "mistral-7b-instruct-v0.2")

# --- ElevenLabs (optional TTS provider) ---
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")

# --- Kokoro (optional local TTS server, English only) ---
KOKORO_API_URL = os.getenv("KOKORO_API_URL", "http://localhost:8880/v1/audio/speech")

# --- Audio playback speed (applied to every TTS provider's output via
# ffmpeg's atempo filter, since not all providers support speed control
# natively). 1.0 = normal, 0.85 = noticeably slower, good for learners. ---
TTS_SPEED = float(os.getenv("TTS_SPEED", "0.85"))

# --- Telegram ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
APPROVAL_TIMEOUT_SECONDS = int(os.getenv("APPROVAL_TIMEOUT_SECONDS", "3600"))

# --- Google Drive / YouTube ---
GOOGLE_CLIENT_SECRETS_FILE = os.getenv("GOOGLE_CLIENT_SECRETS_FILE", "client_secret.json")
GOOGLE_DRIVE_FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
YOUTUBE_CATEGORY_ID = os.getenv("YOUTUBE_CATEGORY_ID", "27")

# --- Render backend: "ffmpeg_local" now, "api_service" later (same interface) ---
RENDER_BACKEND = os.getenv("RENDER_BACKEND", "ffmpeg_local")
FFMPEG_BINARY = os.getenv("FFMPEG_BINARY", "ffmpeg")
RENDER_API_URL = os.getenv("RENDER_API_URL", "")  # used only by api_service backend later
RENDER_API_KEY = os.getenv("RENDER_API_KEY", "")

# --- Arabic overlay font (repo-level shared asset, used by pillow_overlay) ---
# Latin-only fonts (Inter etc.) can't render Arabic script — lines containing
# Arabic fall back to these fonts. Missing file = Arabic lines render as boxes.
ROOT_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = ROOT_DIR / "assets"
ARABIC_FONT_BOLD = os.getenv("ARABIC_FONT_BOLD", str(ASSETS_DIR / "fonts" / "NotoSansArabic-Bold.ttf"))
ARABIC_FONT_REGULAR = os.getenv("ARABIC_FONT_REGULAR", str(ASSETS_DIR / "fonts" / "NotoSansArabic-Regular.ttf"))

# --- Edge TTS ("edge" provider) voice map ---
# Maps per-segment language codes to neural voices. The plugin's own target
# voice comes from its config.py TTS_LANG_OR_VOICE (a full voice name like
# "de-DE-KatjaNeural"); segments in OTHER languages (English explanations,
# Arabic translations) resolve through this map. Override via .env if desired.
EDGE_VOICE_MAP = {
    "en": os.getenv("EDGE_VOICE_EN", "en-US-AvaMultilingualNeural"),
    "ar": os.getenv("EDGE_VOICE_AR", "ar-SA-ZariyahNeural"),
    "de": os.getenv("EDGE_VOICE_DE", "de-DE-KatjaNeural"),
    "fr": os.getenv("EDGE_VOICE_FR", "fr-FR-DeniseNeural"),
    "es": os.getenv("EDGE_VOICE_ES", "es-ES-ElviraNeural"),
}

# --- Shared paths ---
TRACKER_DIR = ROOT_DIR / "trackers"
TRACKER_DIR.mkdir(exist_ok=True)
