import os
from dotenv import load_dotenv
import asyncio
import httpx
from typing import Callable

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