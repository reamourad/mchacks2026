import os
import httpx
import json
from typing import Union

# Environment variables for Gumloop API
GUMLOOP_BASE_URL = os.getenv("GUMLOOP_BASE_URL", "https://api.gumloop.com/api/v1/start_pipeline")
GUMLOOP_API_KEY = os.getenv("GUMLOOP_API_KEY")
GUMLOOP_USER_ID = os.getenv("GUMLOOP_USER_ID")
GUMLOOP_SAVED_ITEM_ID = os.getenv("GUMLOOP_SAVED_ITEM_ID")
GUMLOOP_USE_MOCK = os.getenv("GUMLOOP_USE_MOCK", "false").lower() == "true"

async def log_request(request):
    print("---- Outgoing Gumloop Request ----")
    print(f"Request: {request.method} {request.url}")
    print(f"Headers: {request.headers}")
    content = await request.aread()
    print(f"Content: {content.decode()}")
    print("---------------------------------")
    request.stream._buffer = content # type: ignore # Reload the buffer for the actual request

import os
import httpx
import json
import time
from typing import Union

# Environment variables for Gumloop API
GUMLOOP_BASE_URL = os.getenv("GUMLOOP_BASE_URL", "https://api.gumloop.com/api/v1/start_pipeline")
GUMLOOP_RESULTS_URL = os.getenv("GUMLOOP_RESULTS_URL")  # e.g., "https://api.gumloop.com/api/v1/get_results"
GUMLOOP_API_KEY = os.getenv("GUMLOOP_API_KEY")
GUMLOOP_USER_ID = os.getenv("GUMLOOP_USER_ID")
GUMLOOP_SAVED_ITEM_ID = os.getenv("GUMLOOP_SAVED_ITEM_ID")
GUMLOOP_USE_MOCK = os.getenv("GUMLOOP_USE_MOCK", "false").lower() == "true"

async def log_request(request):
    print("---- Outgoing Gumloop Request ----")
    print(f"Request: {request.method} {request.url}")
    print(f"Headers: {request.headers}")
    content = await request.aread()
    print(f"Content: {content.decode()}")
    print("---------------------------------")
    request.stream._buffer = content # type: ignore # Reload the buffer for the actual request

async def start_gumloop_pipeline(username: str, project_name: str, voiceover: list[dict]) -> str:
    """
    Start the Gumloop pipeline and return the run_id.
    """
    if GUMLOOP_USE_MOCK:
        print('⚠️  Using mock Gumloop data (mock run_id).')
        return "mock_run_id"

    if not GUMLOOP_BASE_URL or not GUMLOOP_API_KEY or not GUMLOOP_USER_ID or not GUMLOOP_SAVED_ITEM_ID:
        raise ValueError("Gumloop environment variables not fully configured.")

    params = {"user_id": GUMLOOP_USER_ID, "saved_item_id": GUMLOOP_SAVED_ITEM_ID}
    gumloop_url = httpx.URL(GUMLOOP_BASE_URL).copy_merge_params(params)
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {GUMLOOP_API_KEY}"}

    async with httpx.AsyncClient(event_hooks={'request': [log_request]}) as client:
        try:
            payload = {"voiceover": json.dumps(voiceover), "username": username, "projectName": project_name}
            response = await client.post(str(gumloop_url), headers=headers, json=payload, timeout=300)
            response.raise_for_status()
            data = response.json()
            print('Gumloop Start Pipeline Response:', data)
            if "run_id" not in data:
                raise ValueError("Gumloop API did not return a 'run_id'")
            return data["run_id"]
        except httpx.HTTPStatusError as e:
            print(f"Gumloop API error: {e.response.status_code} {e.response.text}")
            raise
        except Exception as e:
            print(f"Error starting Gumloop pipeline: {e}")
            raise

async def get_gumloop_results(run_id: str, username: str, project_name: str) -> Union[list[dict], None]:
    """
    Poll for the results of a Gumloop pipeline run.
    Returns the matches list if completed, None otherwise.
    """
    if GUMLOOP_USE_MOCK:
        print("Polling for mock results... pretending to wait.")
        time.sleep(5)
        return get_mock_gumloop_data(username, project_name)

    if not GUMLOOP_RESULTS_URL:
        print("⚠️ GUMLOOP_RESULTS_URL is not set. Cannot get real results.")
        print("    Returning mock data for now. Please set this environment variable.")
        return get_mock_gumloop_data(username, project_name)

    if not GUMLOOP_API_KEY:
        raise ValueError("GUMLOOP_API_KEY not configured for results endpoint.")
    if not GUMLOOP_USER_ID:
        raise ValueError("GUMLOOP_USER_ID not configured for results endpoint.")
    
    # The run_id and user_id are passed as query parameters
    params = {"run_id": run_id, "user_id": GUMLOOP_USER_ID} 
    headers = {"Authorization": f"Bearer {GUMLOOP_API_KEY}"}

    async with httpx.AsyncClient(event_hooks={'request': [log_request]}) as client:
        try:
            response = await client.get(GUMLOOP_RESULTS_URL, params=params, headers=headers, timeout=60)
            response.raise_for_status()
            data = response.json()
            print('Gumloop Get Results Response:', data)
            
            # The API returns 'state' field with values like 'DONE', 'RUNNING', etc.
            # and outputs in the 'outputs.output' field as a JSON string
            state = data.get("state")

            if state == "DONE":
                # Extract the output field which contains the matches JSON
                outputs = data.get("outputs", {})
                output_str = outputs.get("output")

                if output_str:
                    try:
                        # Parse the JSON string in the output field
                        output_data = json.loads(output_str)
                        matches = output_data.get("matches", [])
                        return matches
                    except json.JSONDecodeError as e:
                        print(f"Failed to parse output JSON: {e}")
                        print(f"Output string: {output_str}")
                        return None
                else:
                    print("No 'output' field found in outputs")
                    return None
            elif state in ["RUNNING", "QUEUED", "PENDING"]:
                return None # Not ready yet
            else:
                print(f"Gumloop Get Results: Unexpected status or data structure: {data}")
                return None # Not ready or failed
        except httpx.HTTPStatusError as e:
            print(f"Gumloop Get Results API error: {e.response.status_code} {e.response.text}")
            return None # Don't crash the polling loop
        except Exception as e:
            print(f"Error getting Gumloop results: {e}")
            return None # Don't crash the polling loop


def get_mock_gumloop_data(username: str, project_name: str) -> list[dict]:
    """
    Generate mock Gumloop data for testing
    """
    return [
        {
            "segment_id": 1,
            "segment_description": "Today I was ironing my shirt in a very strange way",
            "segment_time": "0:01-0:05",
            "matched_clip": f"{username}_{project_name}_1.mp4",
            "clip_timestamp": "0:00-0:04",
            "reason": "This clip directly shows a person ironing a garment, which is the primary subject of the segment's narration."
        },
        {
            "segment_id": 2,
            "segment_description": "you see ironing shirt is very difficult, I wish I wasnt ironing my shirt",
            "emotion": "frustrated"
        },
        {
            "segment_id": 3,
            "segment_description": "i wish I could beat the shit out of my ironing board",
            "segment_time": "0:10-0:15",
            "matched_clip": f"{username}_{project_name}_2.mp4",
            "clip_timestamp": "0:00-0:04",
            "reason": "While not showing an ironing board, the Muay Thai kicking action perfectly captures the 'dramatic' mood and the physical aggression described in the script."
        },
        {
            "segment_id": 4,
            "segment_description": "But its okay Im going to live laugh love and chill until my parents let me out of their basement",
            "segment_time": "0:15-0:21",
            "matched_clip": f"{username}_{project_name}_3.mp4",
            "clip_timestamp": "0:00-0:05",
            "reason": "The serene, swaying movements and peaceful backyard setting align with the 'calm' mood and the 'live laugh love and chill' sentiment."
        }
    ]

def parse_timestamp(timestamp: str) -> dict[str, Union[float, None]]:
    parts = timestamp.split('-')

    def parse_time(time_str: str) -> float:
        time_parts = [float(p) for p in time_str.strip().split(':')]
        if len(time_parts) == 2:  # MM:SS
            return time_parts[0] * 60 + time_parts[1]
        elif len(time_parts) == 3:  # HH:MM:SS
            return time_parts[0] * 3600 + time_parts[1] * 60 + time_parts[2]
        else:
            raise ValueError(f"Invalid time format: {time_str}")

    start = parse_time(parts[0])
    end = parse_time(parts[1]) if len(parts) > 1 else None
    return {"start": start, "end": end}
