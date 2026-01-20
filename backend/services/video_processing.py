import os
import json
import tempfile
import subprocess
import logging
from pathlib import Path
from typing import Optional

# Set FFMPEG path for Windows before importing moviepy
FFMPEG_PATH = r"C:\ffmpeg\bin\ffmpeg.exe"
FFPROBE_PATH = r"C:\ffmpeg\bin\ffprobe.exe"
if os.path.exists(FFMPEG_PATH):
    os.environ["IMAGEIO_FFMPEG_EXE"] = FFMPEG_PATH
    os.environ["FFMPEG_BINARY"] = FFMPEG_PATH
    os.environ["FFPROBE_BINARY"] = FFPROBE_PATH
    # Add to PATH as well
    os.environ["PATH"] = r"C:\ffmpeg\bin;" + os.environ.get("PATH", "")

from moviepy import VideoFileClip, TextClip, AudioFileClip, CompositeVideoClip, concatenate_videoclips
from PIL import ImageFont, ImageDraw, Image

# Disable MoviePy logging for faster processing
logging.getLogger('moviepy').setLevel(logging.CRITICAL)

# Get the backend directory for font paths
BACKEND_DIR = Path(__file__).parent.parent
FONTS_DIR = BACKEND_DIR / "fonts"


def get_verified_font(font_path: str) -> str:
    """Return font path if exists, otherwise return fallback."""
    if os.path.exists(font_path):
        return font_path
    # Fallback to Arial on Windows or default
    fallbacks = [
        r"C:\Windows\Fonts\arial.ttf",
        r"C:\Windows\Fonts\Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for fb in fallbacks:
        if os.path.exists(fb):
            return fb
    return "Arial"  # Let MoviePy try to find it


def get_styles():
    """Returns emotion-based text styles with font paths."""
    styles = {
        "neutral":    {"color": "yellow",      "font": str(FONTS_DIR / "Playwrite_NG_Modern/static/PlaywriteNGModern-Regular.ttf")},
        "confident":  {"color": "cyan",        "font": str(FONTS_DIR / "Limelight/Limelight-Regular.ttf")},
        "excited":    {"color": "yellow",      "font": str(FONTS_DIR / "Bowlby_One_SC/BowlbyOneSC-Regular.ttf")},
        "happy":      {"color": "lightpink",   "font": str(FONTS_DIR / "Monsieur_La_Doulaise/MonsieurLaDoulaise-Regular.ttf")},
        "serious":    {"color": "white",       "font": str(FONTS_DIR / "Playfair_Display/static/PlayfairDisplay-Regular.ttf")},
        "concerned":  {"color": "lightblue",   "font": str(FONTS_DIR / "Playwrite_NG_Modern/static/PlaywriteNGModern-Light.ttf")},
        "empathetic": {"color": "lightgreen",  "font": str(FONTS_DIR / "Limelight/Limelight-Regular.ttf")},
        "persuasive": {"color": "yellowgreen", "font": str(FONTS_DIR / "Bowlby_One_SC/BowlbyOneSC-Regular.ttf")},
        "reflective": {"color": "lavender",    "font": str(FONTS_DIR / "Monsieur_La_Doulaise/MonsieurLaDoulaise-Regular.ttf")},
        "frustrated": {"color": "orange",      "font": str(FONTS_DIR / "Playfair_Display/static/PlayfairDisplay-Bold.ttf")},
        "urgent":     {"color": "orangered",   "font": str(FONTS_DIR / "Playwrite_NG_Modern/static/PlaywriteNGModern-Thin.ttf")},
        "sad":        {"color": "steelblue",   "font": str(FONTS_DIR / "Limelight/Limelight-Regular.ttf")},
    }
    # Verify all fonts exist, use fallback if not
    for emotion, style in styles.items():
        style["font"] = get_verified_font(style["font"])
    return styles


def get_default_font():
    return str(FONTS_DIR / "Playwrite_NG_Modern/static/PlaywriteNGModern-Regular.ttf")


def time_to_seconds(time_str: str) -> float:
    """Converts HH:MM:SS or MM:SS or SS to total seconds."""
    parts = time_str.split(':')
    if len(parts) == 3:
        h, m, s = map(float, parts)
        return h * 3600 + m * 60 + s
    elif len(parts) == 2:
        m, s = map(float, parts)
        return m * 60 + s
    else:
        return float(parts[0])


def get_text_width(text: str, font_size: int = 50, font_path: Optional[str] = None) -> int:
    """Measure text width using PIL."""
    if font_path is None:
        font_path = get_default_font()
    font = ImageFont.truetype(font_path, font_size)
    img = Image.new('RGB', (1, 1))
    draw = ImageDraw.Draw(img)
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0]


def resize_and_crop_video(clip: VideoFileClip, target_width: int = 1080, target_height: int = 1920):
    """Resize and crop video to target dimensions (9:16 vertical)."""
    target_ratio = target_width / target_height
    current_ratio = clip.w / clip.h

    if abs(current_ratio - target_ratio) > 0.01:
        if current_ratio > target_ratio:
            clip = clip.resized(height=target_height)
            crop_x1 = (clip.w - target_width) / 2
            clip = clip.cropped(x1=crop_x1, y1=0, x2=crop_x1 + target_width, y2=target_height)
        else:
            clip = clip.resized(width=target_width)
            crop_y1 = (clip.h - target_height) / 2
            clip = clip.cropped(x1=0, y1=crop_y1, x2=target_width, y2=crop_y1 + target_height)

    return clip


def merge_video_clips(video_paths: list[str], output_path: str, target_width: int = 1080, target_height: int = 1920) -> str:
    """
    Merge multiple video clips into one.
    Resizes all to target dimensions first.
    Audio is stripped from all clips.
    """
    if len(video_paths) == 0:
        raise ValueError("No video paths provided")

    if len(video_paths) == 1:
        # Single clip - just resize and strip audio
        clip = VideoFileClip(video_paths[0])
        clip = resize_and_crop_video(clip, target_width, target_height)
        clip = clip.without_audio()  # Strip original audio
        clip.write_videofile(output_path, fps=clip.fps, threads=8, preset="ultrafast")
        clip.close()
        return output_path

    # Multiple clips - resize, strip audio, and concatenate
    resized_clips = []
    for path in video_paths:
        clip = VideoFileClip(path)
        clip = resize_and_crop_video(clip, target_width, target_height)
        clip = clip.without_audio()  # Strip original audio
        resized_clips.append(clip)

    final = concatenate_videoclips(resized_clips, method="chain")
    final.write_videofile(output_path, fps=final.fps, threads=8, preset="ultrafast")

    # Clean up
    for clip in resized_clips:
        clip.close()
    final.close()

    return output_path


def add_subtitles_to_video(
    video_path: str,
    transcript_data: list[dict],
    output_path: str,
    audio_path: Optional[str] = None,
    target_width: int = 1080,
    target_height: int = 1920,
) -> str:
    """
    Add subtitles to video based on transcript data.

    transcript_data format:
    [
        {"start": "00:00:00", "end": "00:00:05", "text": "Hello world", "emotion": "neutral"},
        ...
    ]
    """
    video = VideoFileClip(video_path)
    video = resize_and_crop_video(video, target_width, target_height)

    styles = get_styles()
    subtitle_clips = []
    max_width_ratio = 0.9
    max_height_ratio = 0.2
    font_size = 75

    print(f"[Subtitles] Processing {len(transcript_data)} transcript entries")
    print(f"[Subtitles] Video dimensions: {video.w}x{video.h}")

    for idx, entry in enumerate(transcript_data):
        start_s = time_to_seconds(entry['start'])
        end_s = time_to_seconds(entry['end'])
        total_duration = end_s - start_s

        if total_duration <= 0:
            total_duration = 0.5

        words = entry.get('text', '').split()
        if not words:
            continue

        emotion = entry.get('emotion', 'neutral')
        style = styles.get(emotion, styles['neutral'])
        text_color = style['color']
        font_path = style['font']

        # Dynamic chunking based on text width
        chunks = []
        current_chunk = []
        max_width = video.w * max_width_ratio

        for word in words:
            test_text = ' '.join(current_chunk + [word])
            if get_text_width(test_text, font_size, font_path) <= max_width:
                current_chunk.append(word)
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = [word]

        if current_chunk:
            chunks.append(current_chunk)

        num_chunks = len(chunks)
        if num_chunks == 0:
            continue

        chunk_duration = total_duration / num_chunks

        for i, chunk in enumerate(chunks):
            chunk_text = ' '.join(chunk)
            chunk_start = start_s + i * chunk_duration

            if idx == 0 and i == 0:
                print(f"[Subtitles] First subtitle: '{chunk_text}' at {chunk_start}s")
                print(f"[Subtitles] Using font: {font_path}, color: {text_color}")

            try:
                txt_clip = TextClip(
                    text=chunk_text,
                    font_size=font_size,
                    font=font_path,
                    color=text_color,
                    stroke_color='black',
                    stroke_width=1.5,
                    method='caption',
                    size=(int(max_width), int(video.h * max_height_ratio))
                ).with_start(chunk_start).with_duration(chunk_duration).with_position(('center', 0.7), relative=True)

                subtitle_clips.append(txt_clip)
            except Exception as e:
                print(f"[Subtitles] Error creating text clip: {e}")
                # Try with fallback font
                try:
                    txt_clip = TextClip(
                        text=chunk_text,
                        font_size=font_size,
                        font="Arial",
                        color=text_color,
                        stroke_color='black',
                        stroke_width=1.5,
                        method='caption',
                        size=(int(max_width), int(video.h * max_height_ratio))
                    ).with_start(chunk_start).with_duration(chunk_duration).with_position(('center', 0.7), relative=True)
                    subtitle_clips.append(txt_clip)
                except Exception as e2:
                    print(f"[Subtitles] Fallback also failed: {e2}")

    # Composite video with subtitles
    print(f"[Subtitles] Created {len(subtitle_clips)} subtitle clips")
    final_video = CompositeVideoClip([video] + subtitle_clips)

    # Write video without audio first
    video_only_path = output_path.replace(".mp4", "_noaudio.mp4")
    final_video.write_videofile(
        video_only_path,
        fps=video.fps,
        threads=8,
        preset="ultrafast",
    )

    # Close clips to release file handles
    video.close()
    final_video.close()
    for clip in subtitle_clips:
        clip.close()

    # Add audio using ffmpeg directly (more reliable)
    if audio_path:
        print(f"[Audio] Adding audio using ffmpeg: {audio_path}")
        ffmpeg_cmd = [
            FFMPEG_PATH,
            "-y",  # Overwrite output
            "-i", video_only_path,  # Video input
            "-i", audio_path,  # Audio input
            "-c:v", "copy",  # Copy video stream
            "-c:a", "aac",  # Encode audio as AAC
            "-b:a", "192k",  # Audio bitrate
            "-map", "0:v:0",  # Use video from first input
            "-map", "1:a:0",  # Use audio from second input
            "-async", "1",  # Sync audio
            output_path
        ]
        print(f"[Audio] Running: {' '.join(ffmpeg_cmd)}")
        result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"[Audio] ffmpeg error: {result.stderr}")
            print(f"[Audio] ffmpeg stdout: {result.stdout}")
            # Fallback - just use video without audio
            import shutil
            shutil.move(video_only_path, output_path)
        else:
            print(f"[Audio] Audio added successfully")
            # Clean up video-only file
            try:
                os.remove(video_only_path)
            except:
                pass
    else:
        # No audio - just rename
        import shutil
        shutil.move(video_only_path, output_path)

    # Clean up
    video.close()
    final_video.close()

    return output_path


async def process_project_export(
    clip_paths: list[str],
    transcript_data: list[dict],
    output_path: str,
    audio_path: Optional[str] = None,
    target_width: int = 1080,
    target_height: int = 1920,
) -> str:
    """
    Full export pipeline:
    1. Merge clips (audio stripped)
    2. Add subtitles
    3. Add voiceover audio
    4. Return output path
    """
    print(f"[Export] Starting export with {len(clip_paths)} clips")
    print(f"[Export] Transcript has {len(transcript_data)} segments")
    print(f"[Export] Audio path: {audio_path}")
    print(f"[Export] Fonts dir: {FONTS_DIR}, exists: {FONTS_DIR.exists()}")

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
        # Step 1: Merge clips
        merged_path = os.path.join(temp_dir, "merged.mp4")
        merge_video_clips(clip_paths, merged_path, target_width, target_height)

        # Step 2: Add subtitles (and audio if provided)
        if transcript_data:
            add_subtitles_to_video(
                merged_path,
                transcript_data,
                output_path,
                audio_path=audio_path,
                target_width=target_width,
                target_height=target_height,
            )
        else:
            # No subtitles - just copy merged video
            if audio_path:
                # Add audio to merged video
                video = VideoFileClip(merged_path)
                audio = AudioFileClip(audio_path)
                video = video.with_audio(audio)
                video.write_videofile(output_path, fps=video.fps, threads=8, preset="ultrafast")
                video.close()
            else:
                # Just move the merged file
                import shutil
                shutil.move(merged_path, output_path)

    return output_path
