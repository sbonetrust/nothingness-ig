#!/usr/bin/env python3
"""
setup.py - Interactive setup wizard for Nothingness IG

Walks you through configuring Azure AI Foundry credentials
and tests the connection before saving.

Usage:
    python setup.py
"""

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
ENV_PATH = PROJECT_ROOT / ".env"


def banner():
    print()
    print("=" * 55)
    print("  Nothingness IG - Setup Wizard")
    print("  Automated Instagram Reel Generator")
    print("=" * 55)
    print()


def test_azure_connection(endpoint: str, api_key: str, deployment: str) -> bool:
    """Test Azure OpenAI chat connection."""
    try:
        from openai import AzureOpenAI
        client = AzureOpenAI(
            azure_endpoint=endpoint,
            api_key=api_key,
            api_version="2025-04-01-preview",
        )
        response = client.chat.completions.create(
            model=deployment,
            messages=[{"role": "user", "content": "Say 'connected' in one word."}],
            max_tokens=10,
        )
        reply = response.choices[0].message.content.strip().lower()
        return "connect" in reply
    except Exception as e:
        print(f"\n  Connection failed: {e}")
        return False


def test_pollinations() -> bool:
    """Test Pollinations.ai image generation."""
    import requests
    try:
        url = "https://image.pollinations.ai/prompt/test%20image?width=256&height=256&nologo=true&private=true"
        print("  Requesting test image from Pollinations.ai...")
        response = requests.get(url, timeout=60)
        return response.status_code == 200 and len(response.content) > 1000
    except Exception as e:
        print(f"\n  Pollinations.ai test failed: {e}")
        return False


def main():
    banner()

    # Step 1: Azure AI Foundry for text generation
    print("STEP 1: Azure AI Foundry (for script generation)")
    print("-" * 50)
    print()
    print("You need a GPT-4o (or GPT-4o-mini) deployment in Azure.")
    print()
    print("How to get this:")
    print("  1. Go to https://ai.azure.com")
    print("  2. Open your project (or create one)")
    print("  3. Go to 'Model catalog' -> search 'gpt-4o'")
    print("  4. Click 'Deploy' -> 'Deploy to a real-time endpoint'")
    print("  5. Note the deployment name (e.g., 'gpt-4o')")
    print("  6. Go to your resource in Azure Portal")
    print("  7. Click 'Keys and Endpoint' under Resource Management")
    print("  8. Copy the Endpoint URL and one of the API Keys")
    print()

    endpoint = input("  Azure endpoint URL: ").strip()
    if not endpoint:
        print("  Skipping Azure setup. You can run this again later.")
        return

    api_key = input("  Azure API key: ").strip()
    deployment = input("  Chat deployment name [gpt-4o]: ").strip() or "gpt-4o"

    print("\n  Testing connection...")
    if test_azure_connection(endpoint, api_key, deployment):
        print("  Azure connection successful!")
    else:
        print("  WARNING: Could not verify connection.")
        proceed = input("  Save anyway? (y/n): ").strip().lower()
        if proceed != "y":
            print("  Setup cancelled. Fix credentials and try again.")
            return

    # Step 2: Image generation
    print()
    print()
    print("STEP 2: Image Generation")
    print("-" * 50)
    print()
    print("Default: Pollinations.ai (FREE, no API key needed)")
    print("Images are generated using the Flux model via Pollinations.")
    print()
    print("Testing Pollinations.ai...")
    if test_pollinations():
        print("  Pollinations.ai is working!")
        image_backend = "pollinations"
    else:
        print("  WARNING: Pollinations.ai is not reachable.")
        print("  You can still use --manual flag to provide your own images.")
        image_backend = "pollinations"

    # Step 3: Instagram (optional)
    print()
    print()
    print("STEP 3: Instagram Credentials (optional, needed only for posting)")
    print("-" * 50)
    print()
    print("You can skip this and add credentials later when ready to post.")
    print()
    ig_user = input("  Instagram username (Enter to skip): ").strip()
    ig_pass = ""
    if ig_user:
        ig_pass = input("  Instagram password: ").strip()

    # Save .env file
    print()
    print()
    print("Saving configuration...")

    env_lines = [
        f"AZURE_OPENAI_ENDPOINT={endpoint}",
        f"AZURE_OPENAI_API_KEY={api_key}",
        f"AZURE_CHAT_DEPLOYMENT={deployment}",
        f"",
        f"# Image generation: 'pollinations' (free) or 'azure' (needs gpt-image-1 deployment)",
        f"IMAGE_BACKEND={image_backend}",
        f"",
    ]

    if ig_user:
        env_lines.extend([
            f"INSTAGRAM_USERNAME={ig_user}",
            f"INSTAGRAM_PASSWORD={ig_pass}",
        ])
    else:
        env_lines.extend([
            f"# INSTAGRAM_USERNAME=your_username",
            f"# INSTAGRAM_PASSWORD=your_password",
        ])

    with open(ENV_PATH, "w") as f:
        f.write("\n".join(env_lines) + "\n")

    print(f"  Saved to: {ENV_PATH}")

    # Summary
    print()
    print("=" * 55)
    print("  Setup complete!")
    print("=" * 55)
    print()
    print(f"  Text generation:  Azure GPT-4o ({deployment})")
    print(f"  Image generation: Pollinations.ai (free)")
    print(f"  Voiceover:        edge-tts (free)")
    print(f"  Video assembly:   MoviePy (local)")
    if ig_user:
        print(f"  Instagram:        @{ig_user}")
    else:
        print(f"  Instagram:        Not configured (run setup.py again to add)")
    print()
    print("  Next steps:")
    print("    1. python generate.py          # Generate your first reel")
    print("    2. python review.py            # Review and approve")
    print("    3. python post.py              # Post to Instagram")
    print()


if __name__ == "__main__":
    main()
