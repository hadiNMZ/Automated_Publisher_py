# Content Pipeline — Monorepo

A local, subscription-free content-automation pipeline, structured as
a monorepo with each content type as a **plugin**. Currently built:
**German, French, Spanish, and English** language-learning tracks.
**Gaming, streamer clips, and anime are placeholders** — planned as
separate future tasks (see `niche_expansion_plan.md`).

## How it works

```
main.py
  -> for each active plugin (german, french, spanish, english):
       core.pipeline.run_plugin(plugin)
         1. generate_content()          <- plugin-specific (language, theme)
         2. generate_audio()             <- plugin's chosen TTS provider/voice
         3. send_audio_for_approval()    <- BLOCKS until you tap Approve/Deny in Telegram
         4. render()                     <- plugin's chosen render backend
         5. send_video_for_approval()    <- BLOCKS until you tap Approve/Deny in Telegram
         6. upload_to_drive() + upload_to_youtube()
```

Every plugin shares the exact same `core/` engine — a plugin is just a
`config.py` declaring its language name, translation languages,
TTS provider/voice, and font paths, plus a thin `generate_content()`
wrapper calling the shared prompt logic.

## Translation logic

- **German / French / Spanish**: phrase in that language, translated
  to **both English and Arabic**
- **English** (its own learning track): phrase in English, translated
  to **Arabic only** (no English→English translation needed)

## Interactive approval (new vs. the original single-language build)

Unlike the earlier German-only project, Telegram approval here is a
**real gate**: `main.py` sends a message with Approve/Deny buttons and
**blocks** (polls Telegram) until you respond, before continuing to
the next step. No more manually running a separate `publish.py`
afterward.

## Render backend: local now, API later

`RENDER_BACKEND` in `.env` picks between:
- `ffmpeg_local` (default) — renders on your machine, for testing
- `api_service` — a template for a future rendering API (Creatomate,
  Shotstack, JSON2Video, etc). Same function signature as
  `ffmpeg_local`, so switching is a one-line `.env` change once you've
  implemented `core/render_backends/api_service.py`.

## Setup

1. `python3 -m venv venv && source venv/bin/activate`
2. `pip install -r requirements.txt`
3. Install ffmpeg (`sudo apt install ffmpeg`) — if your system ffmpeg
   is broken/mismatched (a `No such filter: drawtext` error), find a
   working ffmpeg binary (`which ffmpeg` after checking
   `ffmpeg -filters | grep drawtext`) and set `FFMPEG_BINARY` in
   `.env` to its exact path.
4. Add font files (must support German/French/Spanish accented
   characters) to each plugin's `assets/` folder:
   `plugins/german/assets/Inter-Bold.ttf` and `Inter-Regular.ttf`
   (repeat for french, spanish, english — or symlink the same files).
5. Copy `.env.example` to `.env` and fill in real values.
6. If using LM Studio: load your model, start its local server
   (Developer/Local Server tab), confirm the model identifier matches
   `LMSTUDIO_MODEL` in `.env`.
7. Set up a Telegram bot (@BotFather) and get your chat ID.
8. Set up Google OAuth (Drive + YouTube Data API enabled, download
   `client_secret.json` to the repo root) — first `main.py` run will
   open a browser to authorize.
9. Run `python main.py` — it'll run German, French, Spanish, then
   English in sequence, pausing for your Telegram approval at each
   audio and video stage.

## Adding a new language plugin

1. Copy an existing plugin folder (e.g. `plugins/german/`) to
   `plugins/<newlang>/`
2. Edit its `config.py`: `NAME`, `LANGUAGE_NAME`, translation flags,
   `TTS_PROVIDER`/`TTS_LANG_OR_VOICE`
3. Add font files to its `assets/` folder
4. Add the plugin name to `ACTIVE_PLUGINS` in `main.py`

## Adding a new TTS or render provider

Same registry pattern as before:
- TTS: add a module to `core/tts_providers/`, register it in
  `core/tts_registry.py`'s `PROVIDERS` dict
- Render: add a module to `core/render_backends/`, register it in
  `core/render_backends/__init__.py`'s `BACKENDS` dict
