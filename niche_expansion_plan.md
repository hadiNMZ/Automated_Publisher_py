# Niche Expansion Plan — Gaming, Streamer Clips, Anime

How to extend the existing German Shorts pipeline architecture to the
other three niches. The core pattern (provider registry → render →
Telegram review → Drive/YouTube publish) stays the same across all of
them — what changes per niche is the **content sourcing** and
**render style**.

---

## What carries over unchanged from the German pipeline

- `notify_telegram.py` — same audio/video review pattern
- `upload_drive.py`, `upload_youtube.py`, `google_auth.py` — same OAuth flow
- `tracker.py` pattern — same idea (avoid repeating content), adapted per niche
- `main.py` / `publish.py` two-stage design — generate+review, then manual publish
- The provider-registry pattern itself — swap in new source/render modules the same way TTS providers were swapped

## What's different per niche

Each niche needs its own version of two things: a **content sourcing step**
(replaces `generate_phrase.py`) and a **render step** (replaces
`render_video.py`'s text-overlay approach).

---

## 1. Gaming Highlights

**Content sourcing** — pull recent uploads from your own gaming footage/channel, or scan a source channel/playlist via the YouTube Data API for clip-worthy moments. Since "worth clipping" isn't reliably automatable yet, plan for a **semi-manual first version**: you flag source VODs/timestamps, the AI just handles trimming and caption-writing.

**AI step** — feed clip metadata (or a transcript segment) to an AI agent that:
- picks the most shareable N-second window
- writes a short hook/caption
- suggests a title

**Render step** — crop the source clip to vertical (9:16), no template background needed (real gameplay footage instead), burn in a short caption. ffmpeg crop + drawtext, similar structure to the German renderer but operating on a real video input instead of `lavfi color=`.

**No TTS needed** — raw game audio carries the emotional peak; avoid narrating over it per what performs best (research showed unedited clips with no commentary outperform narrated ones).

**Reused as-is**: Telegram review, Drive archive, YouTube publish.

---

## 2. Streamer Viral Clips

Nearly identical to Gaming Highlights, but the sourcing step is different:

**Content sourcing** — Twitch API's clips endpoint (or a channel's VOD list), filtered by view count / recency / chat activity if available as a signal for "this moment popped."

**AI step** — same idea as gaming: pick best moment, write hook/caption, suggest title. Bias the prompt toward reaction/fail/hype moments specifically (spectacular fails, unexpected wins, genuine surprise reactions) since that's what over-indexes for this content type.

**Render step** — same crop + caption approach as gaming.

**Reused as-is**: everything else.

---

## 3. Anime (Rankings / Debate Content)

The most different of the three — no raw footage sourcing due to copyright constraints. This is closer to the German pipeline's "generate content, then illustrate it" shape than to gaming/streamer clips.

**Content sourcing** — no external API; instead, an AI-generation step similar to `generate_phrase.py`'s pattern:
- Generate a script for a short ranking/debate video (e.g. "Top 5 anime fight scenes" or "Is X the strongest character in Y") — text output, structured JSON like the German pipeline (title, script lines, ranking items)

**Visual step** — since real anime clips are legally risky, source **manga panels, fan art with permission, or AI-generated anime-style stills** instead. This is a new module (not present in the German pipeline) — likely a slideshow-style render: one still image per ranking item, timed to match narration.

**Audio step** — reuse the existing TTS provider registry directly (gTTS/ElevenLabs/Kokoro all apply here — and this is actually where Kokoro's English-only voices become useful, unlike the German pipeline).

**Render step** — more complex than gaming/German: needs to sequence multiple images with timed narration and captions, closer to a basic slideshow/video-editing script than a single ffmpeg overlay call. Budget extra build time here specifically.

**Reused as-is**: Telegram review, Drive archive, YouTube publish, tracker pattern (avoid repeating rankings/topics).

---

## Suggested build order

1. **Streamer clips** — reuses the most existing infrastructure, simplest new pieces (Twitch API sourcing + crop/caption render)
2. **Gaming highlights** — nearly identical to streamer clips, build right after
3. **Anime** — build last; it's the most novel (new slideshow render logic, new content-sourcing approach, copyright-safe visual sourcing)

Each of these should live as its own project folder (or subfolder) following the same `config.py` / provider-registry / `main.py` + `publish.py` pattern as `german_shorts/`, rather than trying to merge all four niches into one codebase.
