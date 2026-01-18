import os
import asyncio
import httpx
import json
import time

# Creatomate API configuration
CREATOMATE_API_KEY = os.environ.get('CREATOMATE_API_KEY')
CREATOMATE_API_URL = "https://api.creatomate.com/v1/renders"
CREATOMATE_TEMPLATE_ID = os.environ.get('CREATOMATE_TEMPLATE_ID')

if not CREATOMATE_API_KEY:
    raise ValueError("CREATOMATE_API_KEY environment variable not set.")
if not CREATOMATE_TEMPLATE_ID:
    raise ValueError("CREATOMATE_TEMPLATE_ID environment variable not set. Please create a basic video template in Creatomate.")


async def process_video_with_creatomate(matches: list[dict], username: str, project_name: str, source_s3_urls: dict[str, str]) -> str:
    """
    Processes video clips (trimming and concatenation) using the Creatomate API.
    Returns the final video URL.
    """
    print(f"Processing video with Creatomate for {username}/{project_name} with {len(matches)} matches.")

    if not matches:
        raise ValueError("No matches provided for Creatomate processing.")

    # Prepare video elements for Creatomate API
    creatomate_elements = []
    for i, match in enumerate(matches):
        s3_key = match.get("matched_clip")
        clip_timestamp = match.get("clip_timestamp")
        
        if not s3_key or not clip_timestamp:
            print(f"Warning: Match {i} missing required fields, skipping.")
            continue

        s3_url = source_s3_urls.get(s3_key)
        if not s3_url:
            print(f"Warning: S3 URL not found for {s3_key}, skipping match {i}.")
            continue

        start_time_str, end_time_str = clip_timestamp.split('-')
        start_time_parts = [float(p) for p in start_time_str.split(':')]
        end_time_parts = [float(p) for p in end_time_str.split(':')]

        trim_start = (start_time_parts[0] * 3600 if len(start_time_parts) == 3 else start_time_parts[0] * 60) + \
                     (start_time_parts[1] if len(start_time_parts) >= 2 else 0) + \
                     (start_time_parts[2] if len(start_time_parts) == 3 else 0)

        trim_end = (end_time_parts[0] * 3600 if len(end_time_parts) == 3 else end_time_parts[0] * 60) + \
                   (end_time_parts[1] if len(end_time_parts) >= 2 else 0) + \
                   (end_time_parts[2] if len(end_time_parts) == 3 else 0)
        
        trim_duration = trim_end - trim_start

        creatomate_elements.append({
            "type": "video",
            "track": 1,  # All videos on the same track will be concatenated
            "source": s3_url,
            "trim_start": trim_start,
            "trim_duration": trim_duration,
            "output_format": "mp4",
        })
    
    if not creatomate_elements:
        raise ValueError("No valid Creatomate elements could be generated from matches.")

    # Construct the Creatomate render request payload
    payload = {
        "template_id": CREATOMATE_TEMPLATE_ID,
        "modifications": [
            {
                "elements": creatomate_elements,
            }
        ],
        "output_format": "mp4",
    }

    headers = {
        "Authorization": f"Bearer {CREATOMATE_API_KEY}",
        "Content-Type": "application/json"
    }

    render_id = None
    try:
        async with httpx.AsyncClient() as client:
            # 1. Send render request
            print("Sending render request to Creatomate...")
            response = await client.post(CREATOMATE_API_URL, headers=headers, json=payload, timeout=300)
            response.raise_for_status()
            render_data = response.json()
            render_id = render_data.get('id')
            render_status = render_data.get('status')
            final_video_url = render_data.get('url')

            print(f"Creatomate render initiated. Render ID: {render_id}, Status: {render_status}")

            # 2. Poll for render status
            if render_id:
                status_url = f"{CREATOMATE_API_URL}/{render_id}"
                max_polls = 60  # Poll for up to 5 minutes (60 * 5 seconds)
                for i in range(max_polls):
                    await asyncio.sleep(5)
                    status_response = await client.get(status_url, headers=headers)
                    status_response.raise_for_status()
                    status_data = status_response.json()
                    current_status = status_data.get('status')
                    progress = status_data.get('progress', 0)
                    final_video_url = status_data.get('url') # Update URL in case it becomes available later

                    print(f"Polling Creatomate render {render_id}. Status: {current_status}, Progress: {progress}%")

                    if current_status == 'succeeded':
                        print(f"Creatomate render succeeded! Final URL: {final_video_url}")
                        return final_video_url
                    elif current_status == 'failed':
                        raise Exception(f"Creatomate render failed. Details: {status_data.get('errors')}")
            else:
                raise Exception("Creatomate render ID not returned in initial response.")

            raise Exception("Creatomate render timed out.")

    except httpx.HTTPStatusError as e:
        print(f"Creatomate API error: {e.response.status_code} {e.response.text}")
        raise Exception(f"Creatomate API error: {e.response.status_code} {e.response.text}")
    except Exception as e:
        print(f"Error processing video with Creatomate: {e}")
        raise

# Existing (now unused) MoviePy/FFmpeg functions - kept for reference if needed
# def cut_clip(input_path: str, output_path: str, start_time: float, end_time: float):
#     pass
# def assemble_video(clip_paths: list[str], output_path: str, temp_dir: str):
#     pass