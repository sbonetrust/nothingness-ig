"""
Instagram posting module - uses instagrapi to upload Reels and manage posting.
"""

import os
import time
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


def get_client():
    """Create and authenticate Instagram client."""
    from instagrapi import Client

    username = os.getenv("INSTAGRAM_USERNAME")
    password = os.getenv("INSTAGRAM_PASSWORD")

    if not username or not password:
        raise ValueError(
            "Instagram credentials not set. "
            "Set INSTAGRAM_USERNAME and INSTAGRAM_PASSWORD in your .env file."
        )

    cl = Client()

    # Try to load saved session first (avoids re-login)
    session_path = Path(__file__).parent.parent / ".ig_session.json"
    if session_path.exists():
        try:
            cl.load_settings(str(session_path))
            cl.login(username, password)
            cl.get_timeline_feed()  # Test if session is valid
            print("  Loaded existing Instagram session.")
            return cl
        except Exception:
            print("  Saved session expired, logging in fresh...")

    cl.login(username, password)
    cl.dump_settings(str(session_path))
    print("  Logged in to Instagram successfully.")
    return cl


def post_reel(
    video_path: str,
    caption: str,
    hashtags: list[str],
    config: dict,
) -> dict:
    """
    Post a Reel to Instagram.

    Args:
        video_path: path to the .mp4 file
        caption: post caption text
        hashtags: list of hashtag strings (without #)
        config: app configuration dict

    Returns:
        dict with post metadata (media_id, url, etc.)
    """
    posting_config = config.get("posting", {})
    disclaimer = posting_config.get("disclaimer", "")
    default_hashtags = posting_config.get("default_hashtags", [])

    # Build full caption
    all_hashtags = list(set(hashtags + default_hashtags))
    hashtag_str = " ".join(f"#{tag}" for tag in all_hashtags)
    full_caption = f"{caption}\n\n{disclaimer}\n\n{hashtag_str}"

    print(f"  Posting reel: {video_path}")
    print(f"  Caption preview: {full_caption[:100]}...")

    cl = get_client()

    media = cl.clip_upload(
        path=video_path,
        caption=full_caption,
    )

    result = {
        "media_id": str(media.id),
        "media_pk": str(media.pk),
        "code": media.code,
        "url": f"https://www.instagram.com/reel/{media.code}/",
    }

    print(f"  Posted successfully: {result['url']}")
    return result
