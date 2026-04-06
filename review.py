#!/usr/bin/env python3
"""
review.py - Review generated Reels before posting

Opens each generated video for preview and lets you approve or reject it.
Approved content moves to output/approved/ for posting.

Usage:
    python review.py          # Review all generated (unreviewed) content
    python review.py --id 3   # Review a specific entry
"""

import argparse
import csv
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent


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


def open_video(video_path: str):
    """Open video file with the system's default player."""
    if platform.system() == "Darwin":  # macOS
        subprocess.Popen(["open", video_path])
    elif platform.system() == "Linux":
        subprocess.Popen(["xdg-open", video_path])
    elif platform.system() == "Windows":
        os.startfile(video_path)


def review_entry(entry_id: str):
    """Review a single generated entry."""
    review_dir = PROJECT_ROOT / "output" / "review" / str(entry_id)
    metadata_path = review_dir / "metadata.json"
    video_path = review_dir / "reel.mp4"
    script_path = review_dir / "script.json"

    if not metadata_path.exists():
        print(f"  No generated content found for entry #{entry_id}")
        return False

    # Load metadata
    with open(metadata_path) as f:
        metadata = json.load(f)

    with open(script_path) as f:
        script = json.load(f)

    print(f"\n{'=' * 60}")
    print(f"  Entry #{entry_id}: {metadata['teacher']} - {metadata['topic']}")
    print(f"{'=' * 60}")
    print(f"\n  Title:    {metadata['title']}")
    print(f"  Overlay:  {metadata['text_overlay']}")
    print(f"\n  Narration:")
    print(f"  {script['narration']}")
    print(f"\n  Caption:")
    print(f"  {metadata['caption']}")
    print(f"\n  Hashtags: {' '.join('#' + h for h in metadata['hashtags'])}")

    # Open video for preview
    if video_path.exists():
        print(f"\n  Opening video preview...")
        open_video(str(video_path))
    else:
        print(f"\n  WARNING: Video file not found at {video_path}")

    # Get user decision
    print(f"\n  Actions:")
    print(f"    [a] Approve  - move to posting queue")
    print(f"    [r] Reject   - mark as pending (regenerate later)")
    print(f"    [s] Skip     - review later")
    print(f"    [q] Quit     - exit review")

    while True:
        choice = input("\n  Your choice: ").strip().lower()
        if choice in ("a", "approve"):
            # Move to approved directory
            approved_dir = PROJECT_ROOT / "output" / "approved" / str(entry_id)
            if approved_dir.exists():
                shutil.rmtree(approved_dir)
            shutil.copytree(review_dir, approved_dir)
            update_status(entry_id, "approved")
            print(f"  APPROVED - Ready for posting.")
            return True
        elif choice in ("r", "reject"):
            update_status(entry_id, "pending")
            # Clean up generated files
            shutil.rmtree(review_dir, ignore_errors=True)
            print(f"  REJECTED - Entry reset to pending. Run generate.py to regenerate.")
            return True
        elif choice in ("s", "skip"):
            print(f"  SKIPPED - Will review later.")
            return True
        elif choice in ("q", "quit"):
            return False
        else:
            print(f"  Invalid choice. Enter a, r, s, or q.")


def main():
    parser = argparse.ArgumentParser(description="Review generated Instagram Reels")
    parser.add_argument("--id", type=str, help="Review a specific entry by ID")
    args = parser.parse_args()

    queue = read_queue()

    if args.id:
        review_entry(args.id)
    else:
        # Review all generated entries
        generated = [e for e in queue if e["status"] == "generated"]
        if not generated:
            print("No content waiting for review.")
            print("Run 'python generate.py' first to generate content.")
            return

        print(f"Found {len(generated)} entries to review.\n")
        for entry in generated:
            cont = review_entry(entry["id"])
            if not cont:
                break

    print("\nReview complete.")
    # Show summary
    queue = read_queue()
    statuses = {}
    for e in queue:
        statuses[e["status"]] = statuses.get(e["status"], 0) + 1
    print(f"Queue status: {statuses}")


if __name__ == "__main__":
    main()
