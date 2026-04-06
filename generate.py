#!/usr/bin/env python3
"""
generate.py - Main content generation pipeline

Processes entries from content_queue.csv and generates complete Instagram Reels:
  1. Generate narration script (Azure AI Foundry LLM)
  2. Generate AI images (Azure AI Foundry gpt-image-1)
  3. Generate voiceover (edge-tts, free)
  4. Assemble video with Ken Burns effect (MoviePy)
  5. Save to output/review/ for human review

Usage:
    python generate.py              # Process next pending entry
    python generate.py --id 3       # Process specific entry by ID
    python generate.py --all        # Process all pending entries
    python generate.py --manual 3   # Use manual images for entry 3
                                    #   (place images in output/review/3/images/)
"""

import argparse
import csv
import json
import os
import sys
import glob
from pathlib import Path

import yaml

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from modules.script_gen import generate_script
from modules.image_gen import generate_images, use_manual_images
from modules.voiceover import generate_voiceover
from modules.video_gen import assemble_video


def load_config() -> dict:
    config_path = PROJECT_ROOT / "config.yaml"
    with open(config_path) as f:
        return yaml.safe_load(f)


def read_queue() -> list[dict]:
    queue_path = PROJECT_ROOT / "content_queue.csv"
    with open(queue_path, newline="") as f:
        return list(csv.DictReader(f))


def write_queue(rows: list[dict]):
    queue_path = PROJECT_ROOT / "content_queue.csv"
    if not rows:
        return
    fieldnames = rows[0].keys()
    with open(queue_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def update_status(entry_id: str, new_status: str):
    rows = read_queue()
    for row in rows:
        if str(row["id"]) == str(entry_id):
            row["status"] = new_status
    write_queue(rows)


def find_bg_music() -> str | None:
    music_dir = PROJECT_ROOT / "assets" / "music"
    if not music_dir.exists():
        return None
    for ext in ("*.mp3", "*.wav", "*.ogg", "*.m4a"):
        files = list(music_dir.glob(ext))
        if files:
            return str(files[0])
    return None


def process_entry(entry: dict, config: dict, use_manual: bool = False):
    """Process a single content queue entry through the full pipeline."""
    entry_id = entry["id"]
    teacher = entry["teacher"]
    topic = entry["topic"]
    quote = entry["quote"]

    output_dir = PROJECT_ROOT / "output" / "review" / str(entry_id)
    output_dir.mkdir(parents=True, exist_ok=True)
    images_dir = output_dir / "images"
    images_dir.mkdir(exist_ok=True)

    print(f"\n{'=' * 60}")
    print(f"Processing entry #{entry_id}: {teacher} - {topic}")
    print(f"{'=' * 60}")

    # Step 1: Generate script
    print("\n[1/4] Generating narration script...")
    script = generate_script(teacher, topic, quote, config)

    # Save script for reference
    script_path = output_dir / "script.json"
    with open(script_path, "w") as f:
        json.dump(script, f, indent=2)
    print(f"  Title: {script['title']}")
    print(f"  Narration: {script['narration'][:80]}...")
    print(f"  Text overlay: {script['text_overlay']}")

    # Step 2: Generate images
    print("\n[2/4] Generating images...")
    if use_manual:
        print("  Using manual images from:", images_dir)
        image_paths = use_manual_images(str(images_dir))
    else:
        image_paths = generate_images(script["image_prompts"], str(images_dir), config)

    # Step 3: Generate voiceover
    print("\n[3/4] Generating voiceover...")
    audio_path = str(output_dir / "voiceover.mp3")
    generate_voiceover(script["narration"], audio_path, config)

    # Step 4: Assemble video
    print("\n[4/4] Assembling video...")
    video_path = str(output_dir / "reel.mp4")
    bg_music = find_bg_music()
    assemble_video(
        image_paths=image_paths,
        voiceover_path=audio_path,
        text_overlay=script["text_overlay"],
        output_path=video_path,
        config=config,
        bg_music_path=bg_music,
    )

    # Save metadata for posting
    metadata = {
        "id": entry_id,
        "teacher": teacher,
        "topic": topic,
        "title": script["title"],
        "caption": script["caption"],
        "hashtags": script["hashtags"],
        "text_overlay": script["text_overlay"],
        "video_path": video_path,
    }
    with open(output_dir / "metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    # Update queue status
    update_status(entry_id, "generated")

    print(f"\n  DONE! Review your reel at: {video_path}")
    print(f"  Run 'python review.py' to approve or reject.")


def main():
    parser = argparse.ArgumentParser(description="Generate Instagram Reels from content queue")
    parser.add_argument("--id", type=str, help="Process a specific entry by ID")
    parser.add_argument("--all", action="store_true", help="Process all pending entries")
    parser.add_argument("--manual", type=str, help="Use manual images for given entry ID")
    args = parser.parse_args()

    config = load_config()
    queue = read_queue()

    if args.manual:
        entries = [e for e in queue if str(e["id"]) == args.manual]
        if not entries:
            print(f"Entry #{args.manual} not found in queue.")
            sys.exit(1)
        process_entry(entries[0], config, use_manual=True)

    elif args.id:
        entries = [e for e in queue if str(e["id"]) == args.id]
        if not entries:
            print(f"Entry #{args.id} not found in queue.")
            sys.exit(1)
        if entries[0]["status"] != "pending":
            print(f"Entry #{args.id} is already '{entries[0]['status']}'. Use --manual to reprocess.")
            sys.exit(1)
        process_entry(entries[0], config)

    elif args.all:
        pending = [e for e in queue if e["status"] == "pending"]
        if not pending:
            print("No pending entries in the queue.")
            sys.exit(0)
        print(f"Processing {len(pending)} pending entries...")
        for entry in pending:
            try:
                process_entry(entry, config)
            except Exception as e:
                print(f"\n  ERROR processing entry #{entry['id']}: {e}")
                continue

    else:
        # Process next pending entry
        pending = [e for e in queue if e["status"] == "pending"]
        if not pending:
            print("No pending entries in the queue.")
            print("Add entries to content_queue.csv and try again.")
            sys.exit(0)
        process_entry(pending[0], config)


if __name__ == "__main__":
    main()
