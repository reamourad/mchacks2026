import os
import tempfile
import shutil
import asyncio
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from db import (
    connect_to_mongo,
    close_mongo_connection,
    get_project,
    update_project_status,
    update_project_completed,
)
from s3 import download_from_s3, upload_file_to_s3, generate_final_video_key
from video_processing import upload_to_mux, cut_clip_with_mux, assemble_video
from gumloop import start_gumloop_pipeline, get_gumloop_results, parse_timestamp


app = FastAPI()

# Add CORS middleware to allow requests from Vercel frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with your Vercel domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    await connect_to_mongo()

@app.on_event("shutdown")
async def shutdown_event():
    await close_mongo_connection()

class ProcessRequest(BaseModel):
    projectId: str

class GumloopRequest(BaseModel):
    username: str
    projectName: str
    voiceover: list[dict]

class CreateVideoRequest(BaseModel):
    username: str
    projectName: str
    matches: list[dict]  # Gumloop output matches

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.post("/call_gumloop")
async def call_gumloop_endpoint(request: GumloopRequest):
    """
    Starts a Gumloop pipeline and returns the run_id for polling.
    """
    try:
        run_id = await start_gumloop_pipeline(request.username, request.projectName, request.voiceover)
        return {"run_id": run_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/get_run_results/{run_id}")
async def get_run_results_endpoint(run_id: str):
    """
    Polls the Gumloop results endpoint for a given run_id.
    """
    try:
        matches = await get_gumloop_results(run_id)
        if matches is not None:
            return {"status": "completed", "matches": matches}
        else:
            return {"status": "running"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/create_video")
async def create_video_from_matches(request: CreateVideoRequest):
    """
    Creates a final video from Gumloop matches using Mux for processing.
    """
    temp_dir = tempfile.mkdtemp(prefix=f"xpresso-mux-{request.username}-{request.projectName}-")

    try:
        print(f"Creating video for {request.username}/{request.projectName} with {len(request.matches)} matches using Mux.")

        # 1. Upload source clips to Mux
        source_mux_assets = {}  # Cache S3 key to Mux asset ID
        for match in request.matches:
            s3_key = match.get("matched_clip")
            if not s3_key:
                continue
            
            if s3_key not in source_mux_assets:
                print(f"Processing source video: {s3_key}")
                local_path = os.path.join(temp_dir, f"source_{s3_key}")
                
                print(f"  Downloading from S3...")
                download_from_s3(s3_key, local_path)
                
                print(f"  Uploading to Mux...")
                asset_id = await upload_to_mux(local_path)
                source_mux_assets[s3_key] = asset_id
                print(f"  -> Mux Asset ID: {asset_id}")

        # 2. Create clipped assets on Mux
        clipped_playback_ids = []
        clip_tasks = []

        for i, match in enumerate(request.matches):
            s3_key = match.get("matched_clip")
            clip_timestamp = match.get("clip_timestamp")
            if not s3_key or not clip_timestamp:
                continue

            source_asset_id = source_mux_assets[s3_key]
            times = parse_timestamp(clip_timestamp)
            start_time = times["start"]
            end_time = times["end"]

            if end_time is None:
                print(f"Warning: Match {i} has invalid timestamp, skipping.")
                continue
            
            print(f"Creating Mux clip for {s3_key} from {start_time}s to {end_time}s")
            task = cut_clip_with_mux(source_asset_id, start_time, end_time)
            clip_tasks.append(task)

        # Run all clipping jobs in parallel
        clipped_playback_ids = await asyncio.gather(*clip_tasks)

        if not clipped_playback_ids:
            raise ValueError("No valid clips were created by Mux.")

        # 3. Assemble all clips
        final_video_path = os.path.join(temp_dir, "final_video.mp4")
        print(f"Assembling {len(clipped_playback_ids)} clips into final video.")
        assemble_video(clipped_playback_ids, final_video_path, temp_dir)

        # 4. Upload final video to S3
        final_s3_key = generate_final_video_key(request.username, request.projectName)
        final_video_url = upload_file_to_s3(final_video_path, final_s3_key)

        print(f"Video created successfully: {final_video_url}")

        return {
            "success": True,
            "videoUrl": final_video_url,
            "s3Key": final_s3_key,
            "clipsProcessed": len(clipped_playback_ids),
        }

    except Exception as e:
        print(f"Error creating video with Mux: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Clean up temp directory
        print(f"Cleaning up temp directory: {temp_dir}")
        shutil.rmtree(temp_dir)
# I've removed the old /process endpoint and process_video_task as it's now superseded by the Mux-based flow
# The frontend should now directly call /create_video