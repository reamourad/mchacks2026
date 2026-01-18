import os
import json
from dotenv import load_dotenv
import asyncio
import httpx
import subprocess
import tempfile
from typing import Callable
from moviepy.editor import VideoFileClip, concatenate_videoclips, TextClip, CompositeVideoClip, AudioFileClip
from PIL import ImageFont

# Load environment variables from .env.local in the parent directory
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env.local')
load_dotenv(dotenv_path=dotenv_path)

# Creatomate API configuration
CREATOMATE_API_KEY = os.environ.get('CREATOMATE_API_KEY')
CREATOMATE_API_URL = "https://api.creatomate.com/v1/renders"

if not CREATOMATE_API_KEY:
    raise ValueError("CREATOMATE_API_KEY environment variable not set.")


def parse_timestamp(timestamp_str: str) -> tuple[float, float]:
    """
    Parse timestamp string in format "MM:SS-MM:SS" or "S-S" to (start_seconds, end_seconds).
    """
    start_str, end_str = timestamp_str.split('-')

    def to_seconds(time_str: str) -> float:
        parts = time_str.strip().split(':')
        if len(parts) == 3:  # HH:MM:SS
            return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
        elif len(parts) == 2:  # MM:SS
            return float(parts[0]) * 60 + float(parts[1])
        else:  # Just seconds
            return float(parts[0])

    return to_seconds(start_str), to_seconds(end_str)


async def wait_for_render_complete(render_id: str, timeout: int = 600):
    """Polls a Creatomate render until it's complete."""
    print(f"Waiting for render {render_id} to complete...")

    headers = {
        "Authorization": f"Bearer {CREATOMATE_API_KEY}",
    }

    async with httpx.AsyncClient() as client:
        max_polls = timeout // 5
        for i in range(max_polls):
            try:
                response = await client.get(
                    f"{CREATOMATE_API_URL}/{render_id}",
                    headers=headers,
                    timeout=30
                )
                response.raise_for_status()
                data = response.json()

                status = data.get("status")
                progress = data.get("progress", 0)

                if status == "succeeded":
                    url = data.get("url")
                    print(f"Render {render_id} completed successfully: {url}")
                    return url
                elif status == "failed":
                    error = data.get("error_message", "Unknown error")
                    raise Exception(f"Render {render_id} failed: {error}")

                print(f"Render status: {status}, Progress: {progress}%")
                await asyncio.sleep(5)

            except httpx.HTTPError as e:
                print(f"HTTP error while checking render status: {e}")
                await asyncio.sleep(5)

        raise Exception(f"Render {render_id} did not complete in time.")


async def create_video_from_matches(matches: list[dict], get_s3_url_func: Callable) -> str:
    """
    Creates a final video from matches using Creatomate API.
    Each match should have: matched_clip (S3 key) and clip_timestamp (start-end format).
    Returns the URL of the rendered video from Creatomate.

    This function CUTS the videos at the specified timestamps and concatenates them.
    """
    if not matches:
        raise ValueError("No matches provided")

    print(f"Creating video from {len(matches)} matches using Creatomate...")

    # Build the Creatomate composition with video elements
    elements = []
    current_time = 0  # Track position in timeline

    for i, match in enumerate(matches):
        s3_key = match.get("matched_clip")
        clip_timestamp = match.get("clip_timestamp")

        if not s3_key or not clip_timestamp:
            print(f"Warning: Match {i} missing s3_key or timestamp, skipping.")
            continue

        # Get the S3 URL for the source video
        video_url = get_s3_url_func(s3_key)

        # Parse timestamp (format: "start-end" or "MM:SS-MM:SS")
        try:
            start_time, end_time = parse_timestamp(clip_timestamp)
            duration = end_time - start_time

            if duration <= 0:
                print(f"Warning: Match {i} has invalid duration, skipping.")
                continue

            print(f"Adding clip {i+1}: {s3_key} from {start_time}s to {end_time}s (duration: {duration}s)")

            # Create a video element with trim settings
            element = {
                "type": "video",
                "source": video_url,
                "trim_start": start_time,
                "trim_duration": duration,
                "time": current_time,  # Position in final video timeline
            }

            elements.append(element)
            current_time += duration  # Move timeline forward

        except Exception as e:
            print(f"Warning: Failed to parse timestamp for match {i}: {e}, skipping.")
            continue

    if not elements:
        raise ValueError("No valid clips to process")

    # Calculate total duration for composition
    total_duration = current_time

    # Create the Creatomate template JSON (no template_id needed)
    template = {
        "output_format": "mp4",
        "width": 1920,
        "height": 1080,
        "frame_rate": 30,
        "duration": total_duration,
        "elements": elements
    }

    print(f"Submitting render request to Creatomate with {len(elements)} clips (total duration: {total_duration}s)...")

    # Submit the render request
    headers = {
        "Authorization": f"Bearer {CREATOMATE_API_KEY}",
        "Content-Type": "application/json"
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                CREATOMATE_API_URL,
                headers=headers,
                json=template,
                timeout=30
            )
            response.raise_for_status()
            result = response.json()
        except httpx.HTTPStatusError as e:
            print(f"Creatomate API error: {e.response.status_code} {e.response.text}")
            raise Exception(f"Creatomate API error: {e.response.status_code} {e.response.text}")

    render_id = result.get("id")
    if not render_id:
        raise Exception("No render ID returned from Creatomate")

    print(f"Render submitted successfully. ID: {render_id}")

    # Wait for the render to complete and get the video URL
    video_url = await wait_for_render_complete(render_id, timeout=600)

    print(f"Video rendered successfully: {video_url}")
    return video_url


async def create_merged_video(video_clips: list[dict]) -> str:
    """
    Alternative function to merge video clips using Creatomate.
    video_clips should be a list of dicts with 'url', 'start_time', 'end_time'.
    Returns the URL of the rendered video from Creatomate.
    """
    if not video_clips:
        raise ValueError("No video clips provided")

    print(f"Merging {len(video_clips)} clips using Creatomate...")

    elements = []
    current_time = 0

    for i, clip in enumerate(video_clips):
        url = clip.get("url")
        start_time = clip.get("start_time", 0)
        end_time = clip.get("end_time")

        if not url:
            print(f"Warning: Clip {i} missing URL, skipping.")
            continue

        element = {
            "type": "video",
            "source": url,
            "time": current_time,
        }

        if start_time > 0:
            element["trim_start"] = start_time

        if end_time is not None:
            duration = end_time - start_time
            element["trim_duration"] = duration
            current_time += duration
            print(f"Added clip {i+1}: {url[:50]}... (start: {start_time}s, duration: {duration}s)")
        else:
            # If no end_time, Creatomate will use the full video duration
            print(f"Added clip {i+1}: {url[:50]}... (full duration from {start_time}s)")
            # Can't calculate current_time precisely without duration, set arbitrary value
            current_time += 10  # Placeholder

        elements.append(element)

    if not elements:
        raise ValueError("No valid clips to merge")

    template = {
        "output_format": "mp4",
        "width": 1920,
        "height": 1080,
        "frame_rate": 30,
        "elements": elements
    }

    print(f"Submitting merge request to Creatomate with {len(elements)} clips...")

    headers = {
        "Authorization": f"Bearer {CREATOMATE_API_KEY}",
        "Content-Type": "application/json"
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                CREATOMATE_API_URL,
                headers=headers,
                json=template,
                timeout=30
            )
            response.raise_for_status()
            result = response.json()
        except httpx.HTTPStatusError as e:
            print(f"Creatomate API error: {e.response.status_code} {e.response.text}")
            raise Exception(f"Creatomate API error: {e.response.status_code} {e.response.text}")

    render_id = result.get("id")
    if not render_id:
        raise Exception("No render ID returned from Creatomate")

    print(f"Merge submitted successfully. ID: {render_id}")

    video_url = await wait_for_render_complete(render_id, timeout=600)

    print(f"Video merged successfully: {video_url}")
    return video_url


def concatenate_clips(*clips, target_width=1080, target_height=1920):
    """
    Concatenates 2 or more video clips sequentially (start to finish).
    Resizes all clips to the same target size for compatibility, then uses 'compose' method.

    Args:
        *clips: Variable number of VideoFileClip, TextClip, or other moviepy clips.
        target_width: Target width for resizing (default 1080).
        target_height: Target height for resizing (default 1920).

    Returns:
        A single concatenated video clip.
    """
    if len(clips) < 2:
        raise ValueError("At least 2 clips are required for concatenation.")

    # Resize all clips to target size
    resized_clips = []
    for clip in clips:
        if clip.w != target_width or clip.h != target_height:
            # Resize maintaining aspect ratio, then crop/pad if necessary
            clip = clip.resized(height=target_height) if clip.w / clip.h > target_width / target_height else clip.resized(width=target_width)
            # Crop to exact size
            if clip.w > target_width:
                clip = clip.cropped(x1=(clip.w - target_width)/2, x2=(clip.w + target_width)/2)
            if clip.h > target_height:
                clip = clip.cropped(y1=(clip.h - target_height)/2, y2=(clip.h + target_height)/2)
        resized_clips.append(clip)

    return concatenate_videoclips(resized_clips, method="chain")


def fast_concatenate_videos(video_paths, output_path):
    """
    Fast concatenation using ffmpeg without re-encoding.
    Assumes videos have compatible codecs, resolution, etc.

    Args:
        video_paths: List of video file paths to concatenate.
        output_path: Output video file path.
    """
    # Create a temporary file list for ffmpeg
    list_file = "temp_concat_list.txt"
    with open(list_file, 'w') as f:
        for path in video_paths:
            f.write(f"file '{path}'\n")

    # Run ffmpeg concat
    cmd = [
        'ffmpeg', '-f', 'concat', '-safe', '0', '-i', list_file,
        '-c', 'copy', '-y', output_path
    ]
    subprocess.run(cmd, check=True)

    # Clean up
    os.remove(list_file)


def cut_video_ffmpeg(input_path: str, output_path: str, start_time: float, end_time: float) -> None:
    """
    Cut video using FFmpeg subprocess (more reliable than moviepy).
    """
    duration = end_time - start_time

    cmd = [
        'ffmpeg',
        '-y',  # Overwrite output file
        '-ss', str(start_time),  # Start time
        '-i', input_path,  # Input file
        '-t', str(duration),  # Duration
        '-c:v', 'libx264',  # Video codec
        '-preset', 'medium',  # Encoding speed
        '-crf', '23',  # Quality (lower = better, 18-28 is good range)
        '-c:a', 'aac',  # Audio codec
        '-b:a', '192k',  # Audio bitrate
        '-movflags', '+faststart',  # Enable streaming
        output_path
    ]

    print(f"Running FFmpeg command: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        raise Exception(f"FFmpeg error: {result.stderr}")

    print(f"FFmpeg cut completed: {output_path}")


def resize_and_crop_video_ffmpeg(input_path: str, output_path: str, target_width: int = 1080, target_height: int = 1920) -> None:
    """
    Resize and crop video to target dimensions using FFmpeg.
    """
    # FFmpeg filter to scale and crop to exact dimensions
    filter_complex = f"scale={target_width}:{target_height}:force_original_aspect_ratio=increase,crop={target_width}:{target_height}"

    cmd = [
        'ffmpeg',
        '-y',
        '-i', input_path,
        '-vf', filter_complex,
        '-c:v', 'libx264',
        '-preset', 'medium',
        '-crf', '23',
        '-c:a', 'aac',
        '-b:a', '192k',
        '-movflags', '+faststart',
        output_path
    ]

    print(f"Resizing video: {input_path} -> {output_path}")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        raise Exception(f"FFmpeg resize error: {result.stderr}")

    print(f"Video resized successfully")


def concatenate_videos_ffmpeg(video_paths: list[str], output_path: str) -> None:
    """
    Concatenate videos using FFmpeg (more reliable than moviepy).
    """
    # Create concat file
    concat_file = output_path + ".concat.txt"
    with open(concat_file, 'w') as f:
        for video_path in video_paths:
            # Use absolute path and escape single quotes
            abs_path = os.path.abspath(video_path)
            f.write(f"file '{abs_path}'\n")

    cmd = [
        'ffmpeg',
        '-y',
        '-f', 'concat',
        '-safe', '0',
        '-i', concat_file,
        '-c', 'copy',  # Copy without re-encoding for speed
        output_path
    ]

    print(f"Concatenating {len(video_paths)} videos...")
    result = subprocess.run(cmd, capture_output=True, text=True)

    # Clean up concat file
    if os.path.exists(concat_file):
        os.remove(concat_file)

    if result.returncode != 0:
        raise Exception(f"FFmpeg concat error: {result.stderr}")

    print(f"Videos concatenated successfully: {output_path}")


async def create_video_from_matches_local(matches: list[dict], download_from_s3_func: Callable, temp_dir: str) -> str:
    """
    Creates a final video from matches using FFmpeg subprocess commands.
    Each match should have: matched_clip (S3 key) and clip_timestamp (start-end format).
    Returns the local path to the final concatenated video.

    This function:
    1. Downloads each clip from S3
    2. Cuts the clip based on timestamp using FFmpeg
    3. Resizes/crops each clip to target dimensions
    4. Concatenates all clips together

    Args:
        matches: List of match dictionaries with 'matched_clip' and 'clip_timestamp'
        download_from_s3_func: Function to download files from S3
        temp_dir: Temporary directory for processing

    Returns:
        Path to the final concatenated video file
    """
    if not matches:
        raise ValueError("No matches provided")

    print(f"Creating video from {len(matches)} matches using FFmpeg...")

    cut_clip_paths = []

    try:
        # Step 1: Download and cut each clip
        for i, match in enumerate(matches):
            s3_key = match.get("matched_clip")
            clip_timestamp = match.get("clip_timestamp")

            if not s3_key or not clip_timestamp:
                print(f"Warning: Match {i} missing s3_key or timestamp, skipping.")
                continue

            # Parse timestamp
            try:
                start_time, end_time = parse_timestamp(clip_timestamp)
                duration = end_time - start_time

                if duration <= 0:
                    print(f"Warning: Match {i} has invalid duration, skipping.")
                    continue

                print(f"Processing clip {i+1}: {s3_key} from {start_time}s to {end_time}s (duration: {duration}s)")

                # Download from S3
                local_source_path = os.path.join(temp_dir, f"source_{i}_{os.path.basename(s3_key)}")
                download_from_s3_func(s3_key, local_source_path)

                # Verify file was downloaded
                if not os.path.exists(local_source_path) or os.path.getsize(local_source_path) == 0:
                    print(f"Error: Downloaded file is missing or empty: {local_source_path}")
                    continue

                # Cut the clip using FFmpeg
                print(f"Cutting clip {i+1} with FFmpeg...")
                cut_path = os.path.join(temp_dir, f"cut_{i}.mp4")
                cut_video_ffmpeg(local_source_path, cut_path, start_time, end_time)

                # Resize and crop to target dimensions
                print(f"Resizing clip {i+1}...")
                resized_path = os.path.join(temp_dir, f"resized_{i}.mp4")
                resize_and_crop_video_ffmpeg(cut_path, resized_path, target_width=1080, target_height=1920)

                cut_clip_paths.append(resized_path)

                # Clean up intermediate files
                if os.path.exists(local_source_path):
                    os.remove(local_source_path)
                if os.path.exists(cut_path):
                    os.remove(cut_path)

            except Exception as e:
                print(f"Error processing match {i}: {e}")
                import traceback
                traceback.print_exc()
                continue

        if not cut_clip_paths:
            raise ValueError("No valid clips were processed")

        # Step 2: Concatenate all cut clips
        print(f"Concatenating {len(cut_clip_paths)} clips...")
        final_output_path = os.path.join(temp_dir, "final_video.mp4")
        concatenate_videos_ffmpeg(cut_clip_paths, final_output_path)

        print(f"Video created successfully: {final_output_path}")
        return final_output_path

    except Exception as e:
        print(f"Error in create_video_from_matches_local: {e}")
        import traceback
        traceback.print_exc()
        raise e


def time_to_seconds(time_str: str) -> float:
    """
    Convert time string in format "MM:SS" or "HH:MM:SS" to seconds.
    """
    parts = time_str.split(':')
    if len(parts) == 3:
        hours, minutes, seconds = parts
        return float(hours) * 3600 + float(minutes) * 60 + float(seconds)
    elif len(parts) == 2:
        minutes, seconds = parts
        return float(minutes) * 60 + float(seconds)
    else:
        return float(parts[0])


def get_text_width(text: str, font_size: int, font_path: str) -> int:
    """
    Calculate the width of text in pixels.
    """
    try:
        font = ImageFont.truetype(font_path, font_size)
        bbox = font.getbbox(text)
        return bbox[2] - bbox[0]
    except:
        # Fallback: estimate width
        return len(text) * font_size * 0.6


def get_styles():
    """
    Get emotion-to-style mappings for subtitles.
    """
    EMOTION_STYLES = {
        "neutral":    {"color": "yellow",       "font": "backend/fonts/Playwrite_NG_Modern/static/PlaywriteNGModern-Regular.ttf"},
        "confident":  {"color": "blue",        "font": "backend/fonts/Limelight/Limelight-Regular.ttf"},
        "excited":    {"color": "yellow",      "font": "backend/fonts/Bowlby_One_SC/BowlbyOneSC-Regular.ttf"},
        "happy":      {"color": "lightpink",   "font": "backend/fonts/Monsieur_La_Doulaise/MonsieurLaDoulaise-Regular.ttf"},
        "serious":    {"color": "grey",        "font": "backend/fonts/Playfair_Display/static/PlayfairDisplay-Regular.ttf"},
        "concerned":  {"color": "lightblue",    "font": "backend/fonts/Playwrite_NG_Modern/static/PlaywriteNGModern-Light.ttf"},
        "empathetic": {"color": "lightgreen",   "font": "backend/fonts/Limelight/Limelight-Regular.ttf"},
        "persuasive": {"color": "yellowgreen",  "font": "backend/fonts/Bowlby_One_SC/BowlbyOneSC-Regular.ttf"},
        "reflective": {"color": "lavender",     "font": "backend/fonts/Monsieur_La_Doulaise/MonsieurLaDoulaise-Regular.ttf"},
        "frustrated": {"color": "orange",       "font": "backend/fonts/Playfair_Display/static/PlayfairDisplay-Bold.ttf"},
        "urgent":     {"color": "orangered",    "font": "backend/fonts/Playwrite_NG_Modern/static/PlaywriteNGModern-Thin.ttf"},
        "sad":        {"color": "steelblue",    "font": "backend/fonts/Limelight/Limelight-Regular.ttf"}
    }
    return EMOTION_STYLES


def add_subtitles_to_video(video_path: str, json_path: str, output_path: str, audio_path: str = None):
    """
    Add subtitles to a video based on a transcript JSON file.

    Args:
        video_path: Path to input video file
        json_path: Path to transcript JSON file
        output_path: Path to save output video with subtitles
        audio_path: Optional path to audio file to replace video audio
    """
    video = VideoFileClip(video_path)

    target_width = 1080
    target_height = 1920
    target_ratio = target_width / target_height
    current_ratio = video.w / video.h

    # Crop/resize to target dimensions if needed
    if abs(current_ratio - target_ratio) > 0.01:
        if current_ratio > target_ratio:
            video = video.resized(height=target_height)
            crop_x1 = (video.w - target_width) / 2
            crop_x2 = crop_x1 + target_width
            video = video.cropped(x1=crop_x1, y1=0, x2=crop_x2, y2=target_height)
        else:
            video = video.resized(width=target_width)
            crop_y1 = (video.h - target_height) / 2
            crop_y2 = crop_y1 + target_height
            video = video.cropped(x1=0, y1=crop_y1, x2=target_width, y2=crop_y2)

    # Load transcript data
    with open(json_path, 'r') as f:
        transcript_data = json.load(f)

    styles = get_styles()
    subtitle_clips = []
    max_width_ratio = 0.7
    max_height_ratio = 0.2
    font_size = 75

    for entry in transcript_data:
        start_s = time_to_seconds(entry['start'])
        end_s = time_to_seconds(entry['end'])
        total_duration = end_s - start_s

        if total_duration <= 0:
            total_duration = 0.5  # Minimum duration for short entries

        words = entry['text'].split()
        if not words:
            continue

        emotion = entry.get('emotion', 'neutral')
        style = styles.get(emotion, styles['neutral'])
        text_color = style['color']
        font_path = style['font']

        # Check if font exists, fallback to default if not
        if not os.path.exists(font_path):
            print(f"Warning: Font not found at {font_path}, using default")
            font_path = None  # Will use moviepy default

        # Dynamic chunking
        chunks = []
        current_chunk = []
        max_width = video.w * max_width_ratio

        for word in words:
            test_text = ' '.join(current_chunk + [word])
            if font_path and get_text_width(test_text, font_size, font_path) <= max_width:
                current_chunk.append(word)
            elif len(test_text) * font_size * 0.6 <= max_width:  # Fallback estimation
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

            txt_clip_params = {
                'text': chunk_text,
                'font_size': font_size,
                'color': text_color,
                'stroke_color': 'black',
                'stroke_width': 1.5,
                'method': 'caption',
                'size': (int(video.w * max_width_ratio), int(video.h * max_height_ratio))
            }

            if font_path:
                txt_clip_params['font'] = font_path

            txt_clip = TextClip(**txt_clip_params).with_start(chunk_start).with_duration(chunk_duration).with_position(('center', 0.85), relative=True)

            subtitle_clips.append(txt_clip)

    # Composite video with subtitles
    final_video = CompositeVideoClip([video] + subtitle_clips)

    # Add audio if provided
    if audio_path and os.path.exists(audio_path):
        audio = AudioFileClip(audio_path)
        final_video = final_video.with_audio(audio)

    # Write final video
    final_video.write_videofile(output_path, fps=video.fps, threads=8, preset="ultrafast")

    # Clean up
    video.close()
    for clip in subtitle_clips:
        clip.close()
    final_video.close()