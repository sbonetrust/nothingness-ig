# Nothingness IG - Automated Instagram Reel Generator

Automated pipeline to create spiritual/philosophical Instagram Reels featuring
teachings from **Ashtavakra, Buddha, Jiddu Krishnamurti, and Osho**.

## How It Works

```
content_queue.csv  -->  generate.py  -->  review.py  -->  post.py
   (your topics)     (AI does everything)  (you approve)   (posts to IG)
```

### The Pipeline

| Step | What Happens | Tool Used | Cost |
|------|-------------|-----------|------|
| 1. Script | LLM generates narration, image prompts, caption, hashtags | Azure AI Foundry (GPT-4o) | ~$0.001 |
| 2. Images | AI generates 4 cinematic spiritual images | Pollinations.ai (Flux) | FREE |
| 3. Voice | Text-to-speech narration | edge-tts (Microsoft) | FREE |
| 4. Video | Ken Burns effect + text overlay + audio mixing | MoviePy (local) | FREE |
| 5. Review | You preview and approve/reject | Your eyeballs | FREE |
| 6. Post | Upload Reel to Instagram | instagrapi | FREE |

**Total cost per Reel: ~$0.001** (basically free!)

## Quick Start (3 steps)

### 1. Install ffmpeg

```bash
brew install ffmpeg
```

### 2. Deploy GPT-4o in Azure AI Foundry

This is the **only model you need to deploy**:

1. Go to [ai.azure.com](https://ai.azure.com/)
2. Open your project (or create one)
3. Go to **Model catalog** -> search **"gpt-4o"**
4. Click **Deploy** -> choose **"Standard"** deployment
5. Note your **deployment name** (e.g., "gpt-4o")
6. Go to your resource in [Azure Portal](https://portal.azure.com)
7. Click **Keys and Endpoint** under Resource Management
8. Copy the **Endpoint URL** and one **API Key**

### 3. Run Setup Wizard

```bash
cd ~/my/nothingness-ig
source venv/bin/activate
python setup.py
```

The wizard will:
- Ask for your Azure endpoint, key, and deployment name
- Test the connection
- Test Pollinations.ai (free image generation)
- Optionally configure Instagram credentials
- Save everything to `.env`

**That's it! You're ready to generate reels.**

## Usage

### Generate a Reel

```bash
source venv/bin/activate

# Generate next pending topic from the queue
python generate.py

# Generate a specific entry
python generate.py --id 1

# Generate all pending entries
python generate.py --all
```

### Review and Approve

```bash
python review.py
```

Opens each video for preview. You choose:
- **[a] Approve** - moves to posting queue
- **[r] Reject** - resets to pending (regenerate later)
- **[s] Skip** - review later
- **[q] Quit**

### Post to Instagram

```bash
# Preview what would be posted
python post.py --dry-run

# Post next approved entry
python post.py

# Post all approved entries (5-min delay between posts)
python post.py --all
```

## Adding Content

Edit `content_queue.csv`:

```csv
id,teacher,topic,quote,status
9,Buddha,Letting Go,"In the end only three things matter: how much you loved how gently you lived and how gracefully you let go.",pending
```

Supported teachers: `Ashtavakra`, `Buddha`, `Krishnamurti`, `Osho`
(Add more in `config.yaml` under `content.teachers`)

## Configuration

### Image Generation Backends

| Backend | Cost | API Key? | Set in .env |
|---------|------|----------|-------------|
| **Pollinations.ai** (default) | Free | No | `IMAGE_BACKEND=pollinations` |
| Azure gpt-image-1 | ~$0.04/reel | Yes | `IMAGE_BACKEND=azure` |
| Manual images | Free | No | Use `--manual` flag |

### Change TTS Voice

```bash
edge-tts --list-voices | grep en-
```

| Voice | Description |
|-------|-------------|
| `en-US-AndrewNeural` | Calm, contemplative male (default) |
| `en-US-GuyNeural` | Deep male voice |
| `en-IN-PrabhatNeural` | Indian English male |
| `en-IN-NeerjaNeural` | Indian English female |

Set in `config.yaml` under `voice.name`.

### Background Music

Drop any royalty-free music into `assets/music/`:
- [Pixabay Music](https://pixabay.com/music/search/meditation/) (free)
- [Uppbeat](https://uppbeat.io/browse/music/meditation) (free)

## Project Structure

```
nothingness-ig/
├── setup.py             # Interactive setup wizard
├── generate.py          # Main generation pipeline
├── review.py            # Review and approve content
├── post.py              # Post to Instagram
├── config.yaml          # All configuration
├── content_queue.csv    # Your content topics
├── requirements.txt     # Python dependencies
├── .env                 # Your credentials (not committed)
├── modules/
│   ├── script_gen.py    # LLM script generation (Azure GPT-4o)
│   ├── image_gen.py     # Image gen (Pollinations.ai / Azure)
│   ├── voiceover.py     # Text-to-speech (edge-tts, free)
│   ├── video_gen.py     # Video assembly (MoviePy)
│   └── poster.py        # Instagram upload (instagrapi)
├── assets/
│   └── music/           # Background music files
└── output/
    ├── review/          # Generated, awaiting review
    ├── approved/        # Approved, ready to post
    └── posted/          # Already posted
```

## Tips

1. **Start small**: Generate 2-3 reels, review them, tweak config, then batch.
2. **Vary teachers**: Alternate between all four for variety.
3. **Post timing**: Best for spiritual content: 6-9 AM and 7-10 PM IST.
4. **Background music**: Ambient music makes reels much more engaging.
5. **Review everything**: The review step exists for a reason -- reject anything off.
