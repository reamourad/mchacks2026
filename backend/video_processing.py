import os
from dotenv import load_dotenv
import asyncio
import httpx
from typing import Callable
import json

# Load environment variables from .env.local in the parent directory
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env.local')
load_dotenv(dotenv_path=dotenv_path)

# Creatomate API configuration
CREATOMATE_API_KEY = os.environ.get('CREATOMATE_API_KEY')
CREATOMATE_API_URL = "https://api.creatomate.com/v1/renders"


async def wait_for_render_complete(render_id: str, timeout: int = 300):
    """Polls a Creatomate render until it's complete."""
    print(f"Waiting for render {render_id} to complete...")

    async with httpx.AsyncClient() as client:
        for _ in range(timeout // 5):
            try:
                response = await client.get(
                    f"https://api.creatomate.com/v1/renders/{render_id}",
                    headers={"Authorization": f"Bearer {CREATOMATE_API_KEY}"},
                    timeout=30
                )
                response.raise_for_status()
                data = response.json()

                status = data.get("status")
                if status == "succeeded":
                    print(f"Render {render_id} completed successfully.")
                    return data.get("url")
                elif status == "failed":
                    error = data.get("error_message", "Unknown error")
                    raise Exception(f"Render {render_id} failed: {error}")

                print(f"Render status: {status}")
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
    """
    if not matches:
        raise ValueError("No matches provided")

    print(f"Creating video from {len(matches)} matches using Creatomate...")

    # Build the Creatomate composition with video elements
    elements = []

    for i, match in enumerate(matches):
        s3_key = match.get("matched_clip")
        clip_timestamp = match.get("clip_timestamp")

        if not s3_key or not clip_timestamp:
            print(f"Warning: Match {i} missing s3_key or timestamp, skipping.")
            continue

        # Get the S3 URL for the source video
        video_url = get_s3_url_func(s3_key)

        # Parse timestamp (format: "start-end" or "MM:SS-MM:SS")
        from gumloop import parse_timestamp
        times = parse_timestamp(clip_timestamp)
        start_time = times["start"]
        end_time = times["end"]

        if end_time is None:
            print(f"Warning: Match {i} has invalid timestamp, skipping.")
            continue

        duration = end_time - start_time

        print(f"Adding clip {i+1}: {s3_key} from {start_time}s to {end_time}s (duration: {duration}s)")

        # Create a video element with trim settings
        element = {
            "type": "video",
            "source": video_url,
            "trim_start": start_time,
            "trim_duration": duration,
            "time": "start" if i == 0 else "end",  # Stack clips sequentially
        }

        elements.append(element)

    if not elements:
        raise ValueError("No valid clips to process")

    # Create the Creatomate template JSON
    template = {
        "output_format": "mp4",
        "width": 1920,
        "height": 1080,
        "frame_rate": 30,
        "elements": elements
    }

    print(f"Submitting render request to Creatomate with {len(elements)} clips...")

    # Submit the render request
    async with httpx.AsyncClient() as client:
        response = await client.post(
            CREATOMATE_API_URL,
            headers={
                "Authorization": f"Bearer {CREATOMATE_API_KEY}",
                "Content-Type": "application/json"
            },
            json={"template": template},
            timeout=30
        )
        response.raise_for_status()
        result = response.json()

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

    for i, clip in enumerate(video_clips):
        url = clip.get("url")
        start_time = clip.get("start_time", 0)
        end_time = clip.get("end_time")

        if not url:
            print(f"Warning: Clip {i} missing URL, skipping.")
            continue

        duration = None
        if end_time is not None:
            duration = end_time - start_time

        element = {
            "type": "video",
            "source": url,
            "time": "start" if i == 0 else "end",
        }

        if start_time > 0:
            element["trim_start"] = start_time
        if duration is not None:
            element["trim_duration"] = duration

        elements.append(element)
        print(f"Added clip {i+1}: {url[:50]}... (start: {start_time}s, duration: {duration}s)")

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

    async with httpx.AsyncClient() as client:
        response = await client.post(
            CREATOMATE_API_URL,
            headers={
                "Authorization": f"Bearer {CREATOMATE_API_KEY}",
                "Content-Type": "application/json"
            },
            json={"template": template},
            timeout=30
        )
        response.raise_for_status()
        result = response.json()

    render_id = result.get("id")
    if not render_id:
        raise Exception("No render ID returned from Creatomate")

    print(f"Merge submitted successfully. ID: {render_id}")

    video_url = await wait_for_render_complete(render_id, timeout=600)

    print(f"Video merged successfully: {video_url}")
    return video_url
