import httpx
from typing import Optional
from config import get_settings

settings = get_settings()

ELEVENLABS_API_URL = "https://api.elevenlabs.io/v1"


async def generate_speech(text: str, voice_id: Optional[str] = None) -> Optional[bytes]:
    """
    Generate speech audio from text using ElevenLabs API.
    Returns audio bytes (MP3 format) or None if failed.
    """
    if not settings.elevenlabs_api_key:
        print("ElevenLabs API key not configured")
        return None

    voice = voice_id or settings.elevenlabs_voice_id

    url = f"{ELEVENLABS_API_URL}/text-to-speech/{voice}"

    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": settings.elevenlabs_api_key,
    }

    payload = {
        "text": text,
        "model_id": "eleven_monolingual_v1",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.5,
        }
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, json=payload, headers=headers)

            if response.status_code == 200:
                return response.content
            else:
                print(f"ElevenLabs API error: {response.status_code} - {response.text}")
                return None

    except httpx.TimeoutException:
        print("ElevenLabs API timeout")
        return None
    except Exception as e:
        print(f"ElevenLabs API error: {e}")
        return None


async def get_available_voices() -> list[dict]:
    """
    Get list of available voices from ElevenLabs.
    Returns list of voice objects with id and name.
    """
    if not settings.elevenlabs_api_key:
        return []

    url = f"{ELEVENLABS_API_URL}/voices"

    headers = {
        "xi-api-key": settings.elevenlabs_api_key,
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=headers)

            if response.status_code == 200:
                data = response.json()
                return [
                    {"id": v["voice_id"], "name": v["name"]}
                    for v in data.get("voices", [])
                ]
            else:
                print(f"ElevenLabs API error: {response.status_code}")
                return []

    except Exception as e:
        print(f"ElevenLabs API error: {e}")
        return []
