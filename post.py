#!/usr/bin/env python3
"""
post.py - Post approved Reels to Instagram

Posts content from output/approved/ to Instagram using instagrapi.

Usage:
    python post.py              # Post next approved entry
    python post.py --id 3       # Post a specific approved entry
    python post.py --all        # Post all approved entries (with delays)
    python post.py --dry-run    # Preview what would be posted without posting
"""

import argparse
import csv
import json
import os
import shutil
import sys
import time
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from modules.poster import post_reel


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


def post_entry(entry_id: str, config: dict, dry_run: bool = False) -> bool:
    """Post a single approved entry to Instagram."""
    approved_dir = PROJECT_ROOT / "output" / "approved" / str(entry_id)
    metadata_path = approved_dir / "metadata.json"
    video_path = approved_dir / "reel.mp4"

    if not metadata_path.exists():
        print(f"  No approved content found for entry #{entry_id}")
        return False

    with open(metadata_path) as f:
        metadata = json.load(f)

    print(f"\n{'=' * 60}")
    print(f"  Posting entry #{entry_id}: {metadata['teacher']} - {metadata['topic']}")
    print(f"{'=' * 60}")
    print(f"  Title: {metadata['title']}")
    print(f"  Caption: {metadata['caption'][:80]}...")
    print(f"  Video: {video_path}")

    if dry_run:
        print(f"\n  [DRY RUN] Would post this reel to Instagram.")
        return True

    if not video_path.exists():
        print(f"  ERROR: Video file not found at {video_path}")
        return False

    try:
        result = post_reel(
            video_path=str(video_path),
            caption=metadata["caption"],
            hashtags=metadata["hashtags"],
            config=config,
        )

        # Save post result
        metadata["post_result"] = result
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)

        # Move to posted directory
        posted_dir = PROJECT_ROOT / "output" / "posted" / str(entry_id)
        if posted_dir.exists():
            shutil.rmtree(posted_dir)
        shutil.copytree(approved_dir, posted_dir)
        shutil.rmtree(approved_dir, ignore_errors=True)

        # Also clean up review directory
        review_dir = PROJECT_ROOT / "output" / "review" / str(entry_id)
        shutil.rmtree(review_dir, ignore_errors=True)

        update_status(entry_id, "posted")
        print(f"\n  POSTED: {result.get('url', 'success')}")
        return True

    except Exception as e:
        print(f"\n  ERROR posting: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Post approved Reels to Instagram")
    parser.add_argument("--id", type=str, help="Post a specific entry by ID")
    parser.add_argument("--all", action="store_true", help="Post all approved entries")
    parser.add_argument("--dry-run", action="store_true", help="Preview without posting")
    args = parser.parse_args()

    config = load_config()
    queue = read_queue()

    if args.id:
        post_entry(args.id, config, dry_run=args.dry_run)

    elif args.all:
        approved = [e for e in queue if e["status"] == "approved"]
        if not approved:
            print("No approved entries to post.")
            return

        print(f"Posting {len(approved)} approved entries...")
        for i, entry in enumerate(approved):
            post_entry(entry["id"], config, dry_run=args.dry_run)
            # Add delay between posts to avoid Instagram rate limits
            if not args.dry_run and i < len(approved) - 1:
                delay = 300  # 5 minutes between posts
                print(f"\n  Waiting {delay}s before next post (Instagram rate limit)...")
                time.sleep(delay)

    else:
        # Post next approved entry
        approved = [e for e in queue if e["status"] == "approved"]
        if not approved:
            print("No approved entries to post.")
            print("Run 'python review.py' to approve generated content first.")
            return
        post_entry(approved[0]["id"], config, dry_run=args.dry_run)

    # Show summary
    print("\n" + "-" * 40)
    queue = read_queue()
    statuses = {}
    for e in queue:
        statuses[e["status"]] = statuses.get(e["status"], 0) + 1
    print(f"Queue status: {statuses}")


if __name__ == "__main__":
    main()
