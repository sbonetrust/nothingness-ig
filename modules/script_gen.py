"""
Script generation module - uses Azure AI Foundry (OpenAI-compatible) to generate
narration scripts, image prompts, captions, and hashtags for Instagram Reels.
"""

import json
import os
from openai import AzureOpenAI
from dotenv import load_dotenv

load_dotenv()


def get_client():
    """Create Azure OpenAI client from environment variables."""
    return AzureOpenAI(
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        api_version=os.getenv("AZURE_API_VERSION", "2025-04-01-preview"),
    )


def generate_script(teacher: str, topic: str, quote: str, config: dict) -> dict:
    """
    Generate a complete content script for one Instagram Reel.

    Returns dict with keys:
        - title: short title for the reel
        - narration: full voiceover text (30-60 seconds when spoken)
        - image_prompts: list of 4 detailed image generation prompts
        - text_overlay: short key quote for on-screen text
        - caption: Instagram caption text
        - hashtags: list of relevant hashtags
    """
    teacher_info = config.get("content", {}).get("teachers", {}).get(teacher, {})
    style = teacher_info.get("style", "Spiritual and philosophical")
    tradition = teacher_info.get("tradition", "")
    source = teacher_info.get("source", "")
    full_name = teacher_info.get("full_name", teacher)
    num_images = config.get("image", {}).get("count", 4)
    max_duration = config.get("content", {}).get("max_duration_seconds", 60)
    language = config.get("content", {}).get("language", "English")

    system_prompt = f"""You are a spiritual content creator specializing in the philosophy of nothingness, 
emptiness (shunya), and non-dual awareness. You create content inspired by teachers like 
Ashtavakra, Buddha, Jiddu Krishnamurti, and Osho.

Your tone is: contemplative, profound, accessible, and poetic \u2014 never preachy or dogmatic.
You make ancient wisdom feel alive and relevant to modern seekers."""

    user_prompt = f"""Create an Instagram Reel script based on:

TEACHER: {full_name}
TRADITION: {tradition}
TOPIC: {topic}
KEY QUOTE: \"{quote}\"
SOURCE TEXT: {source}
TEACHER'S STYLE: {style}

REQUIREMENTS:
- Language: {language}
- Narration should be 30-50 seconds when spoken aloud (~75-120 words)
- The narration should feel like a meditation or contemplation, not a lecture
- Start with a hook that grabs attention in the first 3 seconds
- End with a thought that lingers in the mind
- Generate exactly {num_images} image prompts for AI image generation
- Image prompts should describe mystical, cinematic, spiritual scenes (NO text in images, NO faces of real people)
- Image prompts should progress visually to match the narration flow

Return ONLY valid JSON (no markdown, no code blocks) in this exact format:
{{
    "title": "short engaging title (5-8 words)",
    "narration": "the full voiceover text",
    "image_prompts": ["prompt 1", "prompt 2", "prompt 3", "prompt 4"],
    "text_overlay": "the one key quote to display on screen (max 15 words)",
    "caption": "Instagram caption (3-5 thoughtful lines reflecting on the teaching, ending with a question or invitation to reflect)",
    "hashtags": ["hashtag1", "hashtag2", "hashtag3", "hashtag4", "hashtag5", "hashtag6", "hashtag7", "hashtag8"]
}}"""

    client = get_client()
    deployment = os.getenv("AZURE_CHAT_DEPLOYMENT", "gpt-4o")

    response = client.chat.completions.create(
        model=deployment,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.8,
        max_tokens=1500,
    )

    raw = response.choices[0].message.content.strip()

    # Try to parse JSON, handling potential markdown code blocks
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    result = json.loads(raw)

    # Validate required keys
    required = ["title", "narration", "image_prompts", "text_overlay", "caption", "hashtags"]
    for key in required:
        if key not in result:
            raise ValueError(f"LLM response missing required key: {key}")

    # Ensure we have the right number of image prompts
    if len(result["image_prompts"]) < num_images:
        # Pad with variations of existing prompts
        while len(result["image_prompts"]) < num_images:
            idx = len(result["image_prompts"]) % len(result["image_prompts"])
            result["image_prompts"].append(
                result["image_prompts"][idx] + ", different angle, varied composition"
            )

    return result
