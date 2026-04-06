"""
Video assembly module - combines AI-generated images, voiceover, text overlays,
and background music into a finished Instagram Reel using MoviePy.

Features:
- Ken Burns effect (slow zoom/pan) on each image
- Text overlay with semi-transparent background
- Crossfade transitions between segments
- Voiceover + optional background music
- 9:16 vertical format (1080x1920)
"""

import os
import random
import numpy as np
from PIL import Image as PILImage, ImageDraw, ImageFont
from moviepy import (
    VideoClip,
    ImageClip,
    AudioFileClip,
    CompositeVideoClip,
    CompositeAudioClip,
    concatenate_videoclips,
    TextClip,
)
from pathlib import Path


def _load_and_prepare_image(image_path: str, target_w: int, target_h: int, zoom_max: float) -> np.ndarray:
    """Load image and resize to cover the canvas at maximum zoom."""
    img = PILImage.open(image_path).convert("RGB")

    # We need the image large enough that at max zoom it still fills the canvas
    fill_w = int(target_w * zoom_max * 1.05)
    fill_h = int(target_h * zoom_max * 1.05)

    # Resize to cover (maintain aspect ratio)
    img_ratio = img.width / img.height
    fill_ratio = fill_w / fill_h

    if img_ratio > fill_ratio:
        new_h = fill_h
        new_w = int(new_h * img_ratio)
    else:
        new_w = fill_w
        new_h = int(new_w / img_ratio)

    img = img.resize((new_w, new_h), PILImage.LANCZOS)
    return np.array(img), new_w, new_h


def make_ken_burns_clip(
    image_path: str,
    duration: float,
    canvas_size: tuple[int, int] = (1080, 1920),
    zoom_start: float = 1.0,
    zoom_end: float = 1.15,
    direction: str = "random",
) -> VideoClip:
    """
    Create a video clip from a still image with Ken Burns (zoom + pan) effect.

    Args:
        image_path: path to the image file
        duration: clip duration in seconds
        canvas_size: output resolution (width, height)
        zoom_start: initial zoom level
        zoom_end: final zoom level
        direction: pan direction - "in", "out", or "random"
    """
    target_w, target_h = canvas_size
    max_zoom = max(zoom_start, zoom_end)

    img_arr, img_w, img_h = _load_and_prepare_image(image_path, target_w, target_h, max_zoom)

    # Randomize zoom direction for variety
    if direction == "random":
        direction = random.choice(["in", "out"])

    if direction == "out":
        zoom_start, zoom_end = zoom_end, zoom_start

    cx, cy = img_w // 2, img_h // 2

    # Slight random offset for pan effect
    pan_x = random.randint(-int(img_w * 0.02), int(img_w * 0.02))
    pan_y = random.randint(-int(img_h * 0.02), int(img_h * 0.02))

    def make_frame(t):
        progress = t / max(duration, 0.001)
        zoom = zoom_start + (zoom_end - zoom_start) * progress

        # Size of the crop region at current zoom
        crop_w = int(target_w * max_zoom / zoom)
        crop_h = int(target_h * max_zoom / zoom)

        # Center point with pan
        px = int(pan_x * progress)
        py = int(pan_y * progress)

        x1 = max(0, cx + px - crop_w // 2)
        y1 = max(0, cy + py - crop_h // 2)
        x2 = min(img_w, x1 + crop_w)
        y2 = min(img_h, y1 + crop_h)

        # Adjust if we hit edges
        if x2 - x1 < crop_w:
            x1 = max(0, x2 - crop_w)
        if y2 - y1 < crop_h:
            y1 = max(0, y2 - crop_h)

        cropped = img_arr[y1:y2, x1:x2]

        # Resize to target canvas
        frame = np.array(
            PILImage.fromarray(cropped).resize((target_w, target_h), PILImage.LANCZOS)
        )
        return frame

    return VideoClip(make_frame, duration=duration)


def create_text_overlay_frame(
    text: str,
    canvas_size: tuple[int, int],
    font_name: str = "Helvetica",
    font_size: int = 44,
) -> np.ndarray:
    """Create a transparent text overlay image using PIL."""
    w, h = canvas_size
    # Create RGBA image
    overlay = PILImage.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # Try to load font
    try:
        font = ImageFont.truetype(font_name, font_size)
    except (OSError, IOError):
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", font_size)
        except (OSError, IOError):
            font = ImageFont.load_default()

    # Word wrap the text
    max_width = int(w * 0.85)
    words = text.split()
    lines = []
    current_line = ""
    for word in words:
        test = f"{current_line} {word}".strip()
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current_line = test
        else:
            if current_line:
                lines.append(current_line)
            current_line = word
    if current_line:
        lines.append(current_line)

    # Calculate text block dimensions
    line_height = font_size + 12
    block_height = len(lines) * line_height + 40
    block_y = h - block_height - 180  # Position above bottom

    # Draw semi-transparent background
    padding = 30
    draw.rounded_rectangle(
        [padding, block_y - 20, w - padding, block_y + block_height],
        radius=16,
        fill=(0, 0, 0, 140),
    )

    # Draw text lines centered
    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        text_w = bbox[2] - bbox[0]
        x = (w - text_w) // 2
        y = block_y + i * line_height + 10
        # Shadow
        draw.text((x + 2, y + 2), line, font=font, fill=(0, 0, 0, 180))
        # Main text
        draw.text((x, y), line, font=font, fill=(255, 255, 255, 240))

    return np.array(overlay)


def assemble_video(
    image_paths: list[str],
    voiceover_path: str,
    text_overlay: str,
    output_path: str,
    config: dict,
    bg_music_path: str | None = None,
) -> str:
    """
    Assemble a complete Instagram Reel from images, voiceover, and text.

    Args:
        image_paths: list of image file paths
        voiceover_path: path to voiceover .mp3 file
        text_overlay: key quote to display on screen
        output_path: where to save the final .mp4
        config: app configuration dict
        bg_music_path: optional path to background music file

    Returns:
        path to the output video file
    """
    vc = config.get("video", {})
    canvas_w = vc.get("width", 1080)
    canvas_h = vc.get("height", 1920)
    fps = vc.get("fps", 24)
    zoom_start = vc.get("zoom_start", 1.0)
    zoom_end = vc.get("zoom_end", 1.15)
    crossfade = vc.get("crossfade", 0.8)
    bg_vol = vc.get("bg_music_volume", 0.08)
    font = vc.get("font", "Helvetica")
    font_size = vc.get("font_size", 44)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    # Load voiceover to get total duration
    voiceover = AudioFileClip(voiceover_path)
    total_duration = voiceover.duration

    # Calculate per-image duration (accounting for crossfade overlaps)
    num_images = len(image_paths)
    if num_images > 1:
        segment_duration = (total_duration + crossfade * (num_images - 1)) / num_images
    else:
        segment_duration = total_duration

    print(f"  Total duration: {total_duration:.1f}s, {num_images} images, {segment_duration:.1f}s each")

    # Create Ken Burns clips for each image
    clips = []
    for i, img_path in enumerate(image_paths):
        print(f"  Processing image {i + 1}/{num_images}...")
        clip = make_ken_burns_clip(
            img_path,
            duration=segment_duration,
            canvas_size=(canvas_w, canvas_h),
            zoom_start=zoom_start,
            zoom_end=zoom_end,
        )
        clips.append(clip)

    # Concatenate with crossfade transitions
    if len(clips) > 1:
        video = concatenate_videoclips(clips, method="compose", padding=-crossfade)
    else:
        video = clips[0]

    # Trim to match voiceover duration exactly
    video = video.with_duration(total_duration)

    # Create text overlay
    overlay_frame = create_text_overlay_frame(
        text_overlay, (canvas_w, canvas_h), font, font_size
    )
    # Convert RGBA overlay to RGB + mask
    overlay_rgb = overlay_frame[:, :, :3]
    overlay_alpha = overlay_frame[:, :, 3].astype(float) / 255.0

    overlay_clip = (
        ImageClip(overlay_rgb)
        .with_duration(total_duration)
        .with_position(("center", "center"))
    )
    # Create mask from alpha channel
    mask_clip = ImageClip(overlay_alpha, is_mask=True).with_duration(total_duration)
    overlay_clip = overlay_clip.with_mask(mask_clip)

    # Fade in the text overlay after 2 seconds
    fade_in_start = min(2.0, total_duration * 0.15)
    overlay_clip = overlay_clip.with_start(fade_in_start)

    # Composite video + text overlay
    final_video = CompositeVideoClip(
        [video, overlay_clip],
        size=(canvas_w, canvas_h),
    )

    # Build audio track
    audio_tracks = [voiceover]

    if bg_music_path and os.path.exists(bg_music_path):
        print(f"  Adding background music: {bg_music_path}")
        bg_music = AudioFileClip(bg_music_path)
        # Loop if music is shorter than video
        if bg_music.duration < total_duration:
            loops_needed = int(total_duration / bg_music.duration) + 1
            from moviepy import concatenate_audioclips
            bg_music = concatenate_audioclips([bg_music] * loops_needed)
        bg_music = bg_music.with_duration(total_duration).with_volume_scaled(bg_vol)
        audio_tracks.append(bg_music)

    if len(audio_tracks) > 1:
        final_audio = CompositeAudioClip(audio_tracks)
    else:
        final_audio = audio_tracks[0]

    final_video = final_video.with_audio(final_audio)

    # Write output
    print(f"  Rendering video to: {output_path}")
    final_video.write_videofile(
        output_path,
        fps=fps,
        codec="libx264",
        audio_codec="aac",
        preset="medium",
        logger=None,
    )

    # Clean up
    voiceover.close()
    for clip in clips:
        clip.close()
    final_video.close()

    print(f"  Video saved: {output_path}")
    return output_path
