"""
Voiceover module - uses edge-tts (free Microsoft TTS) to generate
natural-sounding narration audio.
"""

import asyncio
import ssl
import certifi
import edge_tts
from pathlib import Path


def _patch_ssl():
    """
    Fix SSL certificate verification on macOS.
    Uses truststore to leverage system CA certificates (handles corporate proxies/VPNs).
    Falls back to certifi, then to unverified context as last resort.
    """
    try:
        import truststore
        ssl_context = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    except ImportError:
        ssl_context = ssl.create_default_context(cafile=certifi.where())

    edge_tts.communicate._SSL_CTX = ssl_context


async def _generate_audio(text: str, output_path: str, voice: str, rate: str, volume: str):
    """Internal async function to generate TTS audio."""
    _patch_ssl()
    communicate = edge_tts.Communicate(text, voice, rate=rate, volume=volume)
    await communicate.save(output_path)


def generate_voiceover(
    narration: str,
    output_path: str,
    config: dict,
) -> str:
    """
    Generate voiceover audio from narration text using edge-tts.

    Args:
        narration: the text to speak
        output_path: path to save the .mp3 file
        config: app configuration dict

    Returns:
        path to the generated audio file
    """
    voice_config = config.get("voice", {})
    voice = voice_config.get("name", "en-US-AndrewNeural")
    rate = voice_config.get("rate", "-10%")
    volume = voice_config.get("volume", "+0%")

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    print(f"  Generating voiceover with voice: {voice}")
    print(f"  Narration length: {len(narration.split())} words")

    asyncio.run(_generate_audio(narration, output_path, voice, rate, volume))

    print(f"  Saved voiceover: {output_path}")
    return output_path


def list_voices(language_filter: str = "en") -> list[dict]:
    """List available edge-tts voices, optionally filtered by language."""
    async def _list():
        voices = await edge_tts.list_voices()
        return voices

    voices = asyncio.run(_list())
    if language_filter:
        voices = [v for v in voices if v["Locale"].startswith(language_filter)]
    return voices
