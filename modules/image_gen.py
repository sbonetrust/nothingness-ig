"""
Image generation module.

Supports two backends:
  1. Pollinations.ai (DEFAULT) - 100% free, no API key, no signup, uses Flux model
  2. Azure AI Foundry (gpt-image-1) - if you have it deployed

Set IMAGE_BACKEND=azure in .env to use Azure. Default is Pollinations.
"""

import os
import time
import base64
import requests
from pathlib import Path
from urllib.parse import quote
from dotenv import load_dotenv

load_dotenv()


def _enhance_prompt(prompt: str) -> str:
    """Add cinematic/spiritual styling to the image prompt."""
    return (
        f"{prompt}. "
        f"Cinematic lighting, mystical atmosphere, ethereal glow, "
        f"8K ultra detailed, spiritual art style, dark moody background, "
        f"no text, no watermarks, no logos."
    )


def _generate_pollinations(prompt: str, output_path: str, config: dict) -> str:
    """Generate an image using Pollinations.ai (free, no API key)."""
    size = config.get("image", {}).get("size", "1024x1536")
    width, height = size.split("x")

    enhanced = _enhance_prompt(prompt)
    encoded_prompt = quote(enhanced)

    url = (
        f"https://image.pollinations.ai/prompt/{encoded_prompt}"
        f"?width={width}&height={height}&model=flux&nologo=true&private=true"
    )

    response = requests.get(url, timeout=180)

    if response.status_code != 200:
        raise RuntimeError(f"Pollinations.ai returned status {response.status_code}")

    with open(output_path, "wb") as f:
        f.write(response.content)

    return output_path


def _generate_azure(prompt: str, output_path: str, config: dict) -> str:
    """Generate an image using Azure AI Foundry (gpt-image-1)."""
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "").rstrip("/")
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    deployment = os.getenv("AZURE_IMAGE_DEPLOYMENT", "gpt-image-1")
    api_version = config.get("azure", {}).get("api_version", "2025-04-01-preview")
    size = config.get("image", {}).get("size", "1024x1536")
    quality = config.get("image", {}).get("quality", "medium")

    enhanced = _enhance_prompt(prompt)

    url = f"{endpoint}/openai/deployments/{deployment}/images/generations?api-version={api_version}"

    response = requests.post(
        url,
        headers={"Api-Key": api_key, "Content-Type": "application/json"},
        json={"prompt": enhanced, "n": 1, "size": size, "quality": quality, "output_format": "png"},
        timeout=120,
    )

    if response.status_code != 200:
        raise RuntimeError(f"Azure image generation failed: {response.text}")

    data = response.json()
    for item in data.get("data", []):
        if "b64_json" in item:
            with open(output_path, "wb") as f:
                f.write(base64.b64decode(item["b64_json"]))
        elif "url" in item:
            img_response = requests.get(item["url"], timeout=60)
            with open(output_path, "wb") as f:
                f.write(img_response.content)

    return output_path


def generate_images(image_prompts: list[str], output_dir: str, config: dict) -> list[str]:
    """
    Generate images from prompts.

    Uses Pollinations.ai (free) by default.
    Set IMAGE_BACKEND=azure in .env to use Azure AI Foundry instead.

    Args:
        image_prompts: list of text prompts
        output_dir: directory to save generated images
        config: app configuration dict

    Returns:
        list of file paths to generated images
    """
    backend = os.getenv("IMAGE_BACKEND", "pollinations").lower()
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    image_paths = []

    for i, prompt in enumerate(image_prompts):
        print(f"  Generating image {i + 1}/{len(image_prompts)} [{backend}]...")
        img_path = os.path.join(output_dir, f"image_{i + 1:02d}.png")

        try:
            if backend == "azure":
                _generate_azure(prompt, img_path, config)
            else:
                _generate_pollinations(prompt, img_path, config)

            image_paths.append(img_path)
            print(f"  Saved: {img_path}")

            # Small delay between requests to be respectful to free APIs
            if backend == "pollinations" and i < len(image_prompts) - 1:
                time.sleep(2)

        except Exception as e:
            print(f"  WARNING: Image {i + 1} failed: {e}")
            continue

    if not image_paths:
        raise RuntimeError(
            "No images were generated. "
            "Check your internet connection or try again. "
            "You can also use --manual to provide your own images."
        )

    return image_paths


def use_manual_images(image_dir: str) -> list[str]:
    """
    Use manually provided images instead of AI generation.
    Place .png or .jpg files in the specified directory.

    Returns:
        sorted list of image file paths
    """
    supported = {".png", ".jpg", ".jpeg", ".webp"}
    images = sorted(
        str(p) for p in Path(image_dir).iterdir()
        if p.suffix.lower() in supported
    )
    if not images:
        raise FileNotFoundError(f"No images found in {image_dir}")
    return images
