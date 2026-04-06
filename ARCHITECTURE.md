# Nothingness IG - Architecture & Guide

> Automated Instagram Reel generator for the philosophy of nothingness.
> Ashtavakra | Buddha | Jiddu Krishnamurti | Osho

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Architecture](#2-architecture)
3. [Data Flow](#3-data-flow)
4. [Components Deep Dive](#4-components-deep-dive)
5. [Directory Structure](#5-directory-structure)
6. [Configuration Reference](#6-configuration-reference)
7. [Prerequisites & Installation](#7-prerequisites--installation)
8. [How to Run](#8-how-to-run)
9. [Content Management](#9-content-management)
10. [Customization](#10-customization)
11. [Troubleshooting](#11-troubleshooting)
12. [Cost Breakdown](#12-cost-breakdown)
13. [Extending the System](#13-extending-the-system)

---

## 1. System Overview

This project is a **semi-automated content pipeline** that transforms spiritual
quotes and topics into finished Instagram Reels. The word "semi" is important —
you remain in the loop to review and approve every piece of content before it
goes live.

### Design Principles

- **Human-in-the-loop**: AI generates, you approve. Nothing posts without your review.
- **Minimal cost**: Only one paid API (Azure GPT-4o at ~$0.001/reel). Everything else is free.
- **Modular**: Each step (script, images, voice, video, posting) is an independent module. Swap any part without touching the others.
- **Offline-capable**: Once content is generated, review and video assembly work entirely offline.
- **No vendor lock-in**: Image generation has multiple backends. Voice uses a free service. LLM can be swapped.

---

## 2. Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        YOUR MACHINE (macOS)                         │
│                                                                     │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐          │
│  │ content_     │    │              │    │              │          │
│  │ queue.csv    │───▶│  generate.py │───▶│  review.py   │──┐      │
│  │              │    │              │    │              │  │      │
│  │  (topics &   │    │  (orchestr-  │    │  (you watch  │  │      │
│  │   quotes)    │    │   ator)      │    │   & approve) │  │      │
│  └──────────────┘    └──────┬───────┘    └──────────────┘  │      │
│                             │                               │      │
│            ┌────────────────┼────────────────┐              │      │
│            │                │                │              │      │
│            ▼                ▼                ▼              ▼      │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────┐ │
│  │ script_gen   │ │ image_gen    │ │ voiceover    │ │ post.py  │ │
│  │              │ │              │ │              │ │          │ │
│  │ Azure GPT-4o │ │ Pollinations │ │ edge-tts     │ │ insta-   │ │
│  │ (narration,  │ │ .ai (Flux)   │ │ (Microsoft   │ │ grapi    │ │
│  │  prompts,    │ │              │ │  TTS, free)  │ │          │ │
│  │  captions)   │ │ FREE, no key │ │              │ │          │ │
│  └──────┬───────┘ └──────┬───────┘ └──────┬───────┘ └────┬─────┘ │
│         │                │                │               │       │
│         └────────────────┼────────────────┘               │       │
│                          ▼                                │       │
│                 ┌──────────────┐                          │       │
│                 │ video_gen    │                          │       │
│                 │              │                          │       │
│                 │ MoviePy      │                          │       │
│                 │ (Ken Burns + │                          │       │
│                 │  text overlay │                         │       │
│                 │  + audio mix)│                          │       │
│                 └──────┬───────┘                          │       │
│                        │                                  │       │
│                        ▼                                  ▼       │
│                 ┌──────────────┐                   ┌───────────┐  │
│                 │ output/      │                   │ Instagram │  │
│                 │  review/     │──(you approve)──▶ │ (Reel)    │  │
│                 │  approved/   │                   └───────────┘  │
│                 │  posted/     │                                  │
│                 └──────────────┘                                  │
└─────────────────────────────────────────────────────────────────────┘

External Services:
  ☁ Azure AI Foundry  ─── GPT-4o chat completions (paid, ~$0.001/call)
  ☁ Pollinations.ai   ─── Flux image generation (free, no auth)
  ☁ Microsoft Edge    ─── Text-to-speech (free, no auth)
  ☁ Instagram API     ─── Reel upload (via instagrapi, unofficial)
```

### Module Dependency Graph

```
generate.py
    ├── modules/script_gen.py    ← Azure OpenAI SDK
    ├── modules/image_gen.py     ← requests (Pollinations / Azure REST)
    ├── modules/voiceover.py     ← edge-tts + truststore (SSL fix)
    └── modules/video_gen.py     ← MoviePy + Pillow + NumPy

review.py
    └── (no module dependencies, uses subprocess to open video player)

post.py
    └── modules/poster.py       ← instagrapi

setup.py
    └── (standalone, tests Azure + Pollinations connectivity)
```

---

## 3. Data Flow

### Per-Reel Generation Pipeline

```
Step 1: SCRIPT GENERATION
┌────────────────────┐        ┌─────────────────────┐
│ Input:             │        │ Output:             │
│  - teacher name    │──LLM──▶│  - narration text   │
│  - topic           │        │  - 4 image prompts  │
│  - seed quote      │        │  - text overlay     │
│  - teacher style   │        │  - caption          │
│                    │        │  - hashtags          │
└────────────────────┘        └─────────┬───────────┘
                                        │
Step 2: IMAGE GENERATION                │
┌────────────────────┐                  │
│ 4 image prompts    │──Pollinations──▶ 4 PNG files (1024×1536)
│ + style enhancement│   .ai / Azure    │
└────────────────────┘                  │
                                        │
Step 3: VOICEOVER                       │
┌────────────────────┐                  │
│ narration text     │──edge-tts──────▶ voiceover.mp3
└────────────────────┘                  │
                                        │
Step 4: VIDEO ASSEMBLY                  │
┌────────────────────┐                  │
│ 4 images           │                  │
│ voiceover.mp3      │──MoviePy──────▶  reel.mp4 (1080×1920)
│ text overlay       │                  │
│ bg music (opt.)    │                  │
└────────────────────┘                  │
                                        ▼
                              ┌───────────────────┐
                              │ output/review/{id} │
                              │  ├── script.json   │
                              │  ├── metadata.json │
                              │  ├── voiceover.mp3 │
                              │  ├── reel.mp4      │
                              │  └── images/       │
                              │       ├── 01.png   │
                              │       ├── 02.png   │
                              │       ├── 03.png   │
                              │       └── 04.png   │
                              └───────────────────┘
```

### Content Lifecycle (Status Transitions)

```
  pending ──── generate.py ────▶ generated ──── review.py ────▶ approved ──── post.py ────▶ posted
     ▲                              │
     └──── review.py (reject) ──────┘
```

| Status | Meaning | Location |
|--------|---------|----------|
| `pending` | Waiting to be generated | `content_queue.csv` only |
| `generated` | AI content created, awaiting review | `output/review/{id}/` |
| `approved` | Human approved, ready to post | `output/approved/{id}/` |
| `posted` | Published to Instagram | `output/posted/{id}/` |

---

## 4. Components Deep Dive

### 4.1 Script Generation (`modules/script_gen.py`)

**Purpose**: Turn a teacher + topic + quote into a complete Reel script.

**How it works**:
1. Loads teacher metadata from `config.yaml` (style, tradition, source text)
2. Constructs a system prompt establishing the "philosophy of nothingness" tone
3. Sends a structured user prompt to GPT-4o requesting JSON output
4. Parses the response and validates all required fields exist
5. Pads image prompts if the model returns fewer than requested

**Input**:
```python
teacher = "Ashtavakra"
topic = "The Self Beyond Mind"
quote = "You are not the body. You are pure awareness."
```

**Output** (JSON):
```json
{
    "title": "The Self That Was Never Bound",
    "narration": "What if everything you believed about yourself was a lie?...",
    "image_prompts": [
        "A lone figure dissolving into cosmic light...",
        "Ancient Sanskrit text floating in dark void...",
        "Shattered mirror reflecting infinite awareness...",
        "Vast empty sky with a single star..."
    ],
    "text_overlay": "You are pure awareness — boundless and free",
    "caption": "Ashtavakra's words cut through centuries...",
    "hashtags": ["ashtavakra", "advaita", "awareness", ...]
}
```

**Key design decisions**:
- Temperature 0.8 for creative variety while maintaining coherence
- Max 1500 tokens to keep narrations concise (30-50 seconds spoken)
- Image prompts explicitly request "no text, no faces of real people"
- JSON output with fallback parsing for markdown code blocks

### 4.2 Image Generation (`modules/image_gen.py`)

**Purpose**: Generate cinematic spiritual images from text prompts.

**Two backends**:

| Backend | How it works | Auth | Cost |
|---------|-------------|------|------|
| **Pollinations.ai** (default) | HTTP GET to `image.pollinations.ai/prompt/{prompt}` | None | Free |
| **Azure gpt-image-1** | REST POST to Azure OpenAI images endpoint | API key | ~$0.01/image |

**Prompt enhancement**: Every prompt is automatically appended with:
> "Cinematic lighting, mystical atmosphere, ethereal glow, 8K ultra detailed,
> spiritual art style, dark moody background, no text, no watermarks, no logos."

**Pollinations.ai details**:
- Uses the **Flux** model (open-source, high quality)
- Images returned as binary directly from the URL
- 2-second delay between requests to respect rate limits
- Default size: 1024×1536 (portrait orientation for 9:16 Reels)
- No signup, no API key, no rate limit published (be respectful)

**Manual image fallback**: `generate.py --manual {id}` skips AI generation
and reads images from `output/review/{id}/images/`.

### 4.3 Voiceover (`modules/voiceover.py`)

**Purpose**: Convert narration text to natural-sounding speech.

**Technology**: [edge-tts](https://github.com/rany2/edge-tts) — a Python
library that uses Microsoft Edge's free TTS service.

**Key features**:
- 200+ voices across 40+ languages
- Neural voices (natural, not robotic)
- Configurable rate and volume
- Completely free, no API key, no limits
- SSL fix for macOS included (uses `truststore` for system CA certificates)

**Default voice**: `en-US-AndrewNeural` (calm male, good for contemplative content)

**Output**: MP3 file with the spoken narration. Duration determines video length.

### 4.4 Video Assembly (`modules/video_gen.py`)

**Purpose**: Combine images, voiceover, and text into a finished Instagram Reel.

**Video specifications**:
- Resolution: 1080×1920 (9:16 vertical, Instagram Reel standard)
- FPS: 24
- Codec: H.264 (libx264) / AAC audio
- Duration: Determined by voiceover length

**Ken Burns Effect**:
```
Each image gets a slow zoom + subtle pan effect:

  Time 0s              Time 5s
  ┌────────────┐       ┌──────────┐
  │            │       │ ┌──────┐ │
  │   IMAGE    │  ──▶  │ │ CROP │ │  (zoomed in)
  │            │       │ └──────┘ │
  └────────────┘       └──────────┘

- Zoom range: 1.0× → 1.15× (configurable)
- Direction randomized per clip (zoom in or zoom out)
- Slight random pan offset for natural camera movement
```

**Text overlay**:
- Positioned near bottom of frame
- Semi-transparent dark background (rounded rectangle)
- White text with drop shadow
- Word-wrapped to 85% of frame width
- Fades in after 2 seconds

**Audio mixing**:
- Voiceover at full volume
- Optional background music at 8% volume (configurable)
- Background music loops if shorter than video
- Composited using MoviePy's `CompositeAudioClip`

**Transitions**: 0.8-second crossfade between image segments.

### 4.5 Instagram Posting (`modules/poster.py`)

**Purpose**: Upload finished Reels to Instagram.

**Technology**: [instagrapi](https://github.com/subzeroid/instagrapi) — Python
library for Instagram's private API.

**Key features**:
- Session persistence (saves to `.ig_session.json` to avoid re-login)
- Caption assembly: combines generated caption + disclaimer + hashtags
- Returns post URL and media ID after upload

**Important notes**:
- Uses Instagram's **unofficial** private API (not Meta's Graph API)
- Risk of account restrictions if used aggressively
- Recommended: max 1-2 posts per day, natural timing
- `post.py --all` adds 5-minute delays between posts automatically
- Alternative: use Meta's official Graph API (requires Business account + Facebook Page)

---

## 5. Directory Structure

```
nothingness-ig/
│
├── setup.py                 # Interactive setup wizard
├── generate.py              # Step 1: Generate content (orchestrator)
├── review.py                # Step 2: Review & approve
├── post.py                  # Step 3: Post to Instagram
│
├── config.yaml              # All configuration (video, voice, teachers, etc.)
├── content_queue.csv        # Content topics and their status
├── requirements.txt         # Python dependencies
├── .env                     # Your API keys (gitignored)
├── .env.example             # Template for .env
├── .gitignore               # Git ignore rules
│
├── modules/                 # Core pipeline modules
│   ├── __init__.py
│   ├── script_gen.py        # LLM script generation
│   ├── image_gen.py         # AI image generation (Pollinations / Azure)
│   ├── voiceover.py         # Text-to-speech (edge-tts)
│   ├── video_gen.py         # Video assembly (MoviePy)
│   └── poster.py            # Instagram upload (instagrapi)
│
├── assets/
│   └── music/               # Drop background music files here
│       └── (your .mp3)      # e.g., ambient_meditation.mp3
│
├── output/                  # All generated content lives here
│   ├── review/              # Generated, waiting for your review
│   │   └── {id}/
│   │       ├── script.json       # LLM output (narration, prompts)
│   │       ├── metadata.json     # Caption, hashtags, paths
│   │       ├── voiceover.mp3     # Spoken narration
│   │       ├── reel.mp4          # Final assembled video
│   │       └── images/
│   │           ├── image_01.png
│   │           ├── image_02.png
│   │           ├── image_03.png
│   │           └── image_04.png
│   ├── approved/            # You approved these, ready to post
│   │   └── {id}/ (same structure)
│   └── posted/              # Successfully posted to Instagram
│       └── {id}/ (same structure)
│
└── venv/                    # Python virtual environment (gitignored)
```

---

## 6. Configuration Reference

### `.env` — Secrets (never committed)

| Variable | Required | Description |
|----------|----------|-------------|
| `AZURE_OPENAI_ENDPOINT` | Yes | Your Azure resource endpoint URL |
| `AZURE_OPENAI_API_KEY` | Yes | Azure API key (KEY 1 or KEY 2) |
| `AZURE_CHAT_DEPLOYMENT` | Yes | Deployment name (e.g., `gpt-4o`) |
| `IMAGE_BACKEND` | No | `pollinations` (default) or `azure` |
| `AZURE_IMAGE_DEPLOYMENT` | Only if azure | Image model deployment name |
| `INSTAGRAM_USERNAME` | For posting | Your Instagram username |
| `INSTAGRAM_PASSWORD` | For posting | Your Instagram password |

### `config.yaml` — All other settings

#### `azure`
| Key | Default | Description |
|-----|---------|-------------|
| `api_version` | `2025-04-01-preview` | Azure OpenAI API version |

#### `video`
| Key | Default | Description |
|-----|---------|-------------|
| `width` | `1080` | Output video width |
| `height` | `1920` | Output video height (9:16 ratio) |
| `fps` | `24` | Frames per second |
| `font` | `Helvetica` | Font for text overlays |
| `font_size` | `44` | Body text size in pixels |
| `title_font_size` | `56` | Title text size in pixels |
| `bg_music_volume` | `0.08` | Background music volume (0.0-1.0) |
| `crossfade` | `0.8` | Transition duration in seconds |
| `zoom_start` | `1.0` | Ken Burns starting zoom level |
| `zoom_end` | `1.15` | Ken Burns ending zoom level |

#### `voice`
| Key | Default | Description |
|-----|---------|-------------|
| `name` | `en-US-AndrewNeural` | edge-tts voice identifier |
| `rate` | `-10%` | Speaking rate (negative = slower) |
| `volume` | `+0%` | Volume adjustment |

#### `image`
| Key | Default | Description |
|-----|---------|-------------|
| `count` | `4` | Number of images per Reel |
| `size` | `1024x1536` | Image dimensions |
| `quality` | `medium` | Quality tier (Azure only) |

#### `content`
| Key | Default | Description |
|-----|---------|-------------|
| `language` | `English` | Output language for scripts |
| `max_duration_seconds` | `60` | Target max Reel duration |
| `teachers` | (see below) | Teacher metadata for prompt engineering |

#### `content.teachers.{name}`
| Key | Description |
|-----|-------------|
| `full_name` | Display name |
| `tradition` | Philosophical tradition |
| `style` | Writing/speaking style description (used in LLM prompt) |
| `source` | Primary source texts |

#### `posting`
| Key | Default | Description |
|-----|---------|-------------|
| `disclaimer` | (see config.yaml) | Added to all posts |
| `default_hashtags` | (see config.yaml) | Added to all posts |

---

## 7. Prerequisites & Installation

### System Requirements

| Requirement | Minimum | Check |
|-------------|---------|-------|
| **macOS / Linux** | macOS 12+ or Ubuntu 20.04+ | — |
| **Python** | 3.10+ | `python3 --version` |
| **ffmpeg** | Any recent | `ffmpeg -version` |
| **Internet** | For API calls | — |
| **Disk space** | ~500MB for venv + output | — |

### Step-by-Step Installation

```bash
# 1. Install ffmpeg (macOS)
brew install ffmpeg

# 2. Navigate to project
cd ~/my/nothingness-ig

# 3. Create virtual environment (already done if you ran setup before)
python3 -m venv venv

# 4. Activate virtual environment
source venv/bin/activate

# 5. Install dependencies
pip install -r requirements.txt

# 6. Run setup wizard
python setup.py
```

### Azure AI Foundry Setup (one-time)

You only need to deploy **one model**: GPT-4o.

1. Go to [ai.azure.com](https://ai.azure.com/)
2. Sign in with your Microsoft account
3. Create a **project** (or open an existing one)
4. Navigate to **Model catalog** in the left sidebar
5. Search for **"gpt-4o"**
6. Click **Deploy** → **Deploy to a real-time endpoint**
7. Choose deployment type: **Standard**
8. Name your deployment (e.g., `gpt-4o`) — remember this name
9. Click **Deploy**
10. Once deployed, go to [Azure Portal](https://portal.azure.com)
11. Find your Azure OpenAI resource
12. Click **Keys and Endpoint** under Resource Management
13. Copy:
    - **Endpoint**: `https://your-resource.openai.azure.com/`
    - **Key**: either KEY 1 or KEY 2

Now run `python setup.py` and paste these values when prompted.

---

## 8. How to Run

### First Time: Generate a Single Reel

```bash
cd ~/my/nothingness-ig
source venv/bin/activate

# Generate the first entry (Ashtavakra - The Self Beyond Mind)
python generate.py --id 1
```

**What happens**:
```
============================================================
Processing entry #1: Ashtavakra - The Self Beyond Mind
============================================================

[1/4] Generating narration script...
  Title: The Self That Was Never Bound
  Narration: What if everything you believed about yourself...
  Text overlay: You are pure awareness — boundless and free

[2/4] Generating images...
  Generating image 1/4 [pollinations]...
  Saved: output/review/1/images/image_01.png
  Generating image 2/4 [pollinations]...
  Saved: output/review/1/images/image_02.png
  ...

[3/4] Generating voiceover...
  Generating voiceover with voice: en-US-AndrewNeural
  Narration length: 87 words
  Saved voiceover: output/review/1/voiceover.mp3

[4/4] Assembling video...
  Total duration: 28.3s, 4 images, 7.7s each
  Processing image 1/4...
  Processing image 2/4...
  ...
  Rendering video to: output/review/1/reel.mp4
  Video saved: output/review/1/reel.mp4

  DONE! Review your reel at: output/review/1/reel.mp4
  Run 'python review.py' to approve or reject.
```

### Review

```bash
python review.py
```

The video opens in your default player. You'll see:
```
============================================================
  Entry #1: Ashtavakra - The Self Beyond Mind
============================================================

  Title:    The Self That Was Never Bound
  Overlay:  You are pure awareness — boundless and free

  Narration:
  What if everything you believed about yourself was a lie?...

  Caption:
  Ashtavakra's words cut through centuries of conditioning...

  Hashtags: #ashtavakra #advaita #awareness #nonduality ...

  Opening video preview...

  Actions:
    [a] Approve  - move to posting queue
    [r] Reject   - mark as pending (regenerate later)
    [s] Skip     - review later
    [q] Quit     - exit review

  Your choice: a
  APPROVED - Ready for posting.
```

### Post to Instagram

```bash
# Always dry-run first to check
python post.py --dry-run

# Post when ready
python post.py --id 1
```

### Batch Workflow

```bash
# Generate all 8 sample entries
python generate.py --all

# Review them all
python review.py

# Post all approved (with 5-min delays)
python post.py --all
```

### Using Your Own Images

If you want to use manually sourced images (e.g., from Bing Image Creator):

```bash
# 1. Create the images folder
mkdir -p output/review/1/images

# 2. Place your images there
cp ~/Downloads/my_image_*.png output/review/1/images/

# 3. Generate with --manual flag (skips AI image generation)
python generate.py --manual 1
```

---

## 9. Content Management

### Adding New Topics

Edit `content_queue.csv`:

```csv
id,teacher,topic,quote,status
9,Buddha,Dependent Origination,"When this exists that comes to be. With the arising of this that arises.",pending
10,Osho,The Art of Dying,"Die each moment so that you can be new each moment.",pending
11,Krishnamurti,Choiceless Awareness,"Can you look at a flower without naming it?",pending
12,Ashtavakra,Beyond Duality,"You are the solitary witness of all that is.",pending
```

**Rules**:
- `id` must be unique (just increment)
- `teacher` must match a key in `config.yaml` → `content.teachers`
- `status` must be `pending` for new entries
- Wrap `quote` in double quotes if it contains commas

### Adding a New Teacher

Edit `config.yaml`:

```yaml
content:
  teachers:
    Rumi:
      full_name: "Jalal ad-Din Muhammad Rumi"
      tradition: "Sufism"
      style: "Ecstatic, poetic, uses metaphors of love and longing. The wound is where the light enters."
      source: "Masnavi, Divan-e Shams"
```

Then use `Rumi` as the teacher in `content_queue.csv`.

---

## 10. Customization

### Video Style

In `config.yaml`:

```yaml
video:
  # Slower, more meditative zoom
  zoom_start: 1.0
  zoom_end: 1.08
  crossfade: 1.2

  # Larger text for quotes
  font_size: 52
```

### Voice

List all available voices:
```bash
source venv/bin/activate
edge-tts --list-voices | grep en-
```

Recommended voices:

| Voice | Tone | Good for |
|-------|------|----------|
| `en-US-AndrewNeural` | Calm, warm male | General spiritual content |
| `en-US-GuyNeural` | Deep, resonant male | Powerful statements |
| `en-US-JennyNeural` | Clear female | Compassion-focused content |
| `en-IN-PrabhatNeural` | Indian English male | Indian philosophy |
| `en-IN-NeerjaNeural` | Indian English female | Softer, nurturing content |
| `en-GB-RyanNeural` | British male | Krishnamurti-style |

### Background Music

Drop an MP3/WAV/OGG/M4A file into `assets/music/`. The first file found
is automatically used as background music for all reels.

Recommended: search "meditation ambient" or "spiritual background" on
[Pixabay Music](https://pixabay.com/music/) (all free, royalty-free).

### Image Backend

Switch in `.env`:

```bash
# Free (default) - Pollinations.ai / Flux model
IMAGE_BACKEND=pollinations

# Azure (if you have gpt-image-1 deployed)
IMAGE_BACKEND=azure
```

### Hashtag Strategy

Edit `config.yaml` → `posting.default_hashtags`. These are added to every post
alongside the hashtags generated by the LLM.

---

## 11. Troubleshooting

### SSL Certificate Error (macOS)

**Symptom**: `SSLCertVerificationError: certificate verify failed`

**Cause**: macOS Python doesn't trust system certificates by default.

**Fix**: Already handled in the code via `truststore`. If it still occurs:
```bash
pip install --upgrade certifi truststore
```

Or as a last resort, run the certificate installer:
```bash
/Applications/Python\ 3.13/Install\ Certificates.command
```

### Image Generation Fails (Pollinations.ai)

**Symptom**: `WARNING: Image 1 failed: Pollinations.ai returned status 5xx`

**Cause**: Pollinations.ai is a free service; it occasionally has downtime.

**Fix**: Wait a few minutes and try again. Or use manual images:
```bash
python generate.py --manual {id}
```

### Video Assembly: Font Not Found

**Symptom**: Text overlay uses a tiny default font.

**Fix**: Set an explicit font path in `config.yaml`:
```yaml
video:
  font: "/System/Library/Fonts/Helvetica.ttc"
```

### Instagram Login Failed

**Symptom**: `instagrapi` can't log in.

**Causes and fixes**:
1. **Wrong credentials**: Double-check `.env`
2. **Two-factor auth**: Disable 2FA or use an app-specific password
3. **Suspicious login**: Instagram may block new locations. Log in manually first on the same machine, then retry
4. **Rate limit**: Wait 24 hours and try again

### MoviePy Import Error

**Symptom**: `ModuleNotFoundError` for moviepy components.

**Fix**: Ensure you're in the virtual environment:
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### Azure API: 401 Unauthorized

**Symptom**: Script generation fails with authentication error.

**Fix**: Verify your `.env` values:
1. Endpoint should end with `/` (e.g., `https://xxx.openai.azure.com/`)
2. API key should be the raw key string, no quotes
3. Deployment name must match exactly what you named it in Azure

Re-run `python setup.py` to test and reconfigure.

---

## 12. Cost Breakdown

### Per-Reel Cost

| Component | Service | Cost |
|-----------|---------|------|
| Script generation | Azure GPT-4o (~1500 tokens) | ~$0.001 |
| Image generation | Pollinations.ai (4 images) | $0.000 |
| Voiceover | edge-tts | $0.000 |
| Video assembly | Local (MoviePy) | $0.000 |
| Instagram posting | instagrapi | $0.000 |
| **Total per Reel** | | **~$0.001** |

### Monthly Estimates

| Posting frequency | Reels/month | Monthly cost |
|-------------------|-------------|-------------|
| 3x per week | 12 | ~$0.01 |
| 5x per week | 20 | ~$0.02 |
| Daily | 30 | ~$0.03 |

If using Azure gpt-image-1 instead of Pollinations: add ~$0.04 per Reel.

---

## 13. Extending the System

### Adding a New Image Backend

Create a new function in `modules/image_gen.py`:

```python
def _generate_newbackend(prompt: str, output_path: str, config: dict) -> str:
    # Your implementation here
    return output_path
```

Then add it to `generate_images()`:
```python
elif backend == "newbackend":
    _generate_newbackend(prompt, img_path, config)
```

### Adding Multi-Language Support

1. Add voice in `config.yaml` (e.g., `hi-IN-MadhurNeural` for Hindi)
2. Set `content.language: "Hindi"` in `config.yaml`
3. The LLM will generate narration in the specified language

### Scheduling with Cron

To auto-generate content on a schedule:

```bash
# Edit crontab
crontab -e

# Generate one reel every day at 5 AM
0 5 * * * cd /Users/sharathbalaraj/my/nothingness-ig && source venv/bin/activate && python generate.py >> /tmp/nothingness-ig.log 2>&1
```

Note: This only generates — posting still requires your manual review and approval.

### Cross-Posting to YouTube Shorts / TikTok

The generated `reel.mp4` files are standard 9:16 vertical videos.
You can manually upload them to any platform. For automation,
consider adding backends in `modules/poster.py` using:
- YouTube Data API (for Shorts)
- TikTok for Developers API
- Or a service like [upload-post.com](https://upload-post.com)

---

*Built with Azure AI Foundry, Pollinations.ai, edge-tts, MoviePy, and instagrapi.*
