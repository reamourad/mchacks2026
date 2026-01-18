import os
import asyncio
import httpx
import mux_python
from mux_python.rest import ApiException
from mux_python.api.assets_api import AssetsApi
from mux_python.api.uploads_api import UploadsApi
from moviepy.editor import VideoFileClip, concatenate_videoclips, AudioClip
import numpy as np
import tempfile

# Mux API configuration
configuration = mux_python.Configuration(
    username=os.environ.get('MUX_TOKEN_ID'),
    password=os.environ.get('MUX_TOKEN_SECRET'),
)
api_client = mux_python.ApiClient(configuration)
assets_api = AssetsApi(api_client)
uploads_api = UploadsApi(api_client)


async def wait_for_asset_ready(asset_id: str, timeout: int = 300):
    """Polls a Mux asset until its status is 'ready'."""
    print(f"Waiting for asset {asset_id} to become ready...")
    for _ in range(timeout // 5):
        try:
            asset = assets_api.get_asset(asset_id)
            if asset.data.status == 'ready':
                print(f"Asset {asset_id} is ready.")
                return asset.data
            elif asset.data.status == 'errored':
                raise Exception(f"Asset {asset_id} creation failed.")
        except ApiException as e:
            print(f"API exception while checking asset status: {e}")
        await asyncio.sleep(5)
    raise Exception(f"Asset {asset_id} did not become ready in time.")

async def upload_to_mux(file_path: str) -> str:
    """Uploads a local file to Mux and returns the new asset's ID."""
    # 1. Create an upload URL
    create_upload_request = mux_python.CreateUploadRequest(
        cors_origin='*', 
        new_asset_settings=mux_python.CreateAssetRequest(
            playback_policy=[mux_python.PlaybackPolicy.PUBLIC]
        )
    )
    upload_response = uploads_api.create_upload(create_upload_request)
    
    # 2. Upload the file
    async with httpx.AsyncClient() as client:
        with open(file_path, 'rb') as f:
            await client.put(upload_response.data.url, content=f.read(), timeout=300)
    
    asset_id = upload_response.data.asset_id
    await wait_for_asset_ready(asset_id)
    return asset_id

async def cut_clip_with_mux(source_asset_id: str, start_time: float, end_time: float) -> str:
    """Creates a new clipped asset on Mux and returns its playback ID."""
    create_asset_request = mux_python.CreateAssetRequest(
        input=[mux_python.InputSettings(
            url=f"mux://assets/{source_asset_id}",
            start_time=start_time,
            end_time=end_time
        )],
        playback_policy=[mux_python.PlaybackPolicy.PUBLIC]
    )
    clipped_asset_response = assets_api.create_asset(create_asset_request)
    clipped_asset_id = clipped_asset_response.data.id
    
    clipped_asset = await wait_for_asset_ready(clipped_asset_id)
    
    # Return the playback ID, which is used to construct streaming URLs
    return clipped_asset.playback_ids[0].id

def assemble_video(clip_playback_ids: list[str], output_path: str, temp_dir: str):
    """
    Downloads clips from Mux, then concatenates them using MoviePy.
    """
    if not clip_playback_ids:
        raise ValueError("No clips to assemble")

    print(f"\n=== Assembling {len(clip_playback_ids)} clips from Mux ===")
    
    local_clip_paths = []
    try:
        # Download all clips
        for i, playback_id in enumerate(clip_playback_ids, 1):
            clip_url = f"https://stream.mux.com/{playback_id}.mp4"
            local_path = os.path.join(temp_dir, f"clip_{i}.mp4")
            
            print(f"Downloading clip {i}: {clip_url}")
            with httpx.stream("GET", clip_url, follow_redirects=True, timeout=300) as response:
                response.raise_for_status()
                with open(local_path, "wb") as f:
                    for chunk in response.iter_bytes():
                        f.write(chunk)
            
            local_clip_paths.append(local_path)
            print(f"  -> Saved to {local_path}")

        # Load clips with MoviePy
        clips = [VideoFileClip(p) for p in local_clip_paths]

        # Concatenate all clips
        print("\nConcatenating clips with MoviePy...")
        final_clip = concatenate_videoclips(clips, method="compose")

        # Write the final video
        print("Writing final video...")
        final_clip.write_videofile(
            output_path,
            codec='libx264',
            audio_codec='aac',
            temp_audiofile=os.path.join(temp_dir, 'temp-audio-final.m4a'),
            remove_temp=True,
            logger=None
        )
    finally:
        # Clean up moviepy clips
        if 'clips' in locals():
            for clip in clips:
                clip.close()
# The old moviepy-only functions can be removed or kept as fallback
# For now, I'm keeping them here but they are not used by the main logic anymore.

def cut_clip(input_path: str, output_path: str, start_time: float, end_time: float):
    """
    Cut a video clip from start to end time using MoviePy.
    Always ensures audio stream is present (adds silent audio if missing) to prevent concat issues.
    """
    print(f"Cutting clip: {input_path} from {start_time}s to {end_time}s")

    try:
        video = VideoFileClip(input_path)
        clip = video.subclip(start_time, end_time)
        has_audio = clip.audio is not None
        if not has_audio:
            print("No audio detected - adding silent audio track...")
            silent_audio = AudioClip(lambda t: np.array([0, 0]), duration=clip.duration, fps=44100)
            clip = clip.set_audio(silent_audio)
        clip.write_videofile(output_path, codec='libx264', audio_codec='aac', temp_audiofile='temp-audio.m4a', remove_temp=True, logger=None)
        clip.close()
        video.close()
    except Exception as e:
        print(f"✗ Error cutting clip: {e}")
        raise Exception(f"MoviePy error cutting clip: {e}")