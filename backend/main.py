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
from video_processing import cut_clip, assemble_video
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

def find_clip_s3_key(matched_clip_name: str, project: dict) -> str:
    # Expected format: username_projectname_number.mp4
    match = os.path.splitext(matched_clip_name)[0].rsplit('_', 1)
    if not match or not match[1].isdigit():
        raise ValueError(f"Invalid matched clip name format: {matched_clip_name}")
    
    clip_number = int(match[1])
    
    for clip in project.get("clips", []):
        if clip.get("clipNumber") == clip_number:
            return clip["s3Key"]
            
    raise ValueError(f"Clip not found in project: {matched_clip_name} (clip #{clip_number})")


async def process_video_task(project_id: str):
    print(f"Starting video processing for project: {project_id}")
    await update_project_status(project_id, "processing")
    
    project = await get_project(project_id)
    if not project:
        print(f"Project {project_id} not found")
        await update_project_status(project_id, "failed", "Project not found")
        return

    # Use a temporary directory for all processing
    temp_dir = tempfile.mkdtemp(prefix=f"xpresso-{project_id}-")
    
    try:
        # 1. Start Gumloop pipeline and get run_id
        voiceover_script = [
            {"start": "00:00:01", "end": "00:00:05", "speaker": "Speaker", "text": "Today I was ironing my shirt in a very strange way", "emotion": "confused"},
            {"start": "00:00:05", "end": "00:00:10", "speaker": "Speaker", "text": "you see ironing shirt is very difficult, I wish I wasnt ironing my shirt", "emotion": "frustrated"},
            {"start": "00:00:10", "end": "00:00:15", "speaker": "Speaker", "text": "i wish I could beat the shit out of my ironing board", "emotion": "angry"},
            {"start": "00:00:15", "end": "00:00:21", "speaker": "Speaker", "text": "But its okay Im going to live laugh love and chill until my parents let me out of their basement", "emotion": "resigned"}
        ]
        run_id = await start_gumloop_pipeline(project["username"], project["projectName"], voiceover_script)
        
        # 2. Poll for Gumloop results
        gumloop_matches = None
        max_retries = 30 # Poll for 5 minutes (30 * 10 seconds)
        for i in range(max_retries):
            print(f"Polling for Gumloop results (attempt {i+1}/{max_retries})...")
            gumloop_matches = await get_gumloop_results(run_id)
            if gumloop_matches is not None:
                print("Gumloop matches received!")
                break
            await asyncio.sleep(10) # Wait 10 seconds between polls
        
        if gumloop_matches is None:
            raise ValueError("Gumloop pipeline timed out or failed to return matches.")

        # 3. Download clips from S3
        downloaded_clips = {} # Map S3 key to local path
        for match in gumloop_matches:
            s3_key = find_clip_s3_key(match["matched_clip"], project)
            if s3_key not in downloaded_clips:
                local_path = os.path.join(temp_dir, os.path.basename(s3_key))
                download_from_s3(s3_key, local_path)
                downloaded_clips[s3_key] = local_path
        
        # 4. Cut clips
        cut_clip_paths = []
        for i, match in enumerate(gumloop_matches):
            s3_key = find_clip_s3_key(match["matched_clip"], project)
            input_path = downloaded_clips[s3_key]
            
            times = parse_timestamp(match["clip_timestamp"])
            start_time = times["start"]
            end_time = times["end"]
            
            if end_time is None:
                raise ValueError(f"Invalid clip timestamp (no end time): {match['clip_timestamp']}")

            cut_output_path = os.path.join(temp_dir, f"cut-segment-{i+1}.mp4")
            print(f"Cutting segment {i+1}: {input_path} from {start_time}s to {end_time}s")
            cut_clip(input_path, cut_output_path, start_time, end_time)
            cut_clip_paths.append(cut_output_path)

        # 5. Assemble video
        final_video_path = os.path.join(temp_dir, "final-video.mp4")
        print(f"Assembling {len(cut_clip_paths)} clips into final video")
        assemble_video(cut_clip_paths, final_video_path)
        
        # 6. Upload to S3
        final_s3_key = generate_final_video_key(project["username"], project["projectName"])
        final_video_url = upload_file_to_s3(final_video_path, final_s3_key)
        
        # 7. Update project status
        await update_project_completed(project_id, final_video_url, final_s3_key)
        print(f"Project {project_id} completed successfully. Final video at {final_video_url}")

    except Exception as e:
        print(f"Error processing video for project {project_id}: {e}")
        await update_project_status(project_id, "failed", str(e))
    finally:
        # Clean up temp directory
        print(f"Cleaning up temp directory: {temp_dir}")
        shutil.rmtree(temp_dir)


@app.post("/create_video")
async def create_video_from_matches(request: CreateVideoRequest):
    """
    Creates a final video from Gumloop matches.
    Downloads clips from S3, cuts them according to timestamps, concatenates them, and uploads the final video.
    """
    temp_dir = tempfile.mkdtemp(prefix=f"xpresso-{request.username}-{request.projectName}-")

    try:
        print(f"Creating video for {request.username}/{request.projectName} with {len(request.matches)} matches")

        # 1. Download and cut clips based on matches
        cut_clip_paths = []
        cut_clip_s3_urls = []  # Store URLs of uploaded cut clips for debugging
        downloaded_clips = {}  # Cache downloaded files to avoid duplicate downloads

        for i, match in enumerate(request.matches):
            # Extract clip name and timestamp
            matched_clip_name = match.get("matched_clip")
            clip_timestamp = match.get("clip_timestamp")

            if not matched_clip_name or not clip_timestamp:
                print(f"Warning: Match {i} missing required fields, skipping")
                continue

            # Use the matched clip name directly as the S3 key
            # The clips are stored in the bucket root with names like: username_projectname_N.mp4
            s3_key = matched_clip_name

            # Download clip if not already downloaded
            if s3_key not in downloaded_clips:
                local_path = os.path.join(temp_dir, f"source_{matched_clip_name}")
                print(f"Downloading {s3_key} from S3...")
                download_from_s3(s3_key, local_path)
                downloaded_clips[s3_key] = local_path
            else:
                local_path = downloaded_clips[s3_key]
                print(f"Using cached {s3_key}")

            # Parse timestamp and cut clip
            times = parse_timestamp(clip_timestamp)
            start_time = times["start"]
            end_time = times["end"]

            if end_time is None:
                print(f"Warning: Match {i} has invalid timestamp (no end time), skipping")
                continue

            cut_output_path = os.path.join(temp_dir, f"cut_segment_{i+1}.mp4")
            print(f"Cutting segment {i+1}: {matched_clip_name} from {start_time}s to {end_time}s")
            cut_clip(local_path, cut_output_path, start_time, end_time)

            # Upload cut clip to S3 for debugging
            cut_clip_s3_key = f"debug/{request.username}/{request.projectName}/segment_{i+1}_{start_time}-{end_time}.mp4"
            print(f"Uploading cut segment {i+1} to S3: {cut_clip_s3_key}")
            cut_clip_url = upload_file_to_s3(cut_output_path, cut_clip_s3_key)
            cut_clip_s3_urls.append({
                "segment": i+1,
                "source": matched_clip_name,
                "timestamp": clip_timestamp,
                "url": cut_clip_url
            })

            cut_clip_paths.append(cut_output_path)

        if not cut_clip_paths:
            raise ValueError("No valid clips were processed")

        # 2. Assemble all cut clips into final video
        final_video_path = os.path.join(temp_dir, "final_video.mp4")
        print(f"Assembling {len(cut_clip_paths)} clips into final video")
        assemble_video(cut_clip_paths, final_video_path)

        # 3. Upload final video to S3
        final_s3_key = generate_final_video_key(request.username, request.projectName)
        final_video_url = upload_file_to_s3(final_video_path, final_s3_key)

        print(f"Video created successfully: {final_video_url}")

        return {
            "success": True,
            "videoUrl": final_video_url,
            "s3Key": final_s3_key,
            "clipsProcessed": len(cut_clip_paths),
            "debugCutClips": cut_clip_s3_urls  # Individual cut clips for debugging
        }

    except Exception as e:
        print(f"Error creating video: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Clean up temp directory
        print(f"Cleaning up temp directory: {temp_dir}")
        shutil.rmtree(temp_dir)


@app.post("/process")
async def process_video(request: ProcessRequest, background_tasks: BackgroundTasks):
    """
    Starts the video processing in the background.
    """
    project = await get_project(request.projectId)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    background_tasks.add_task(process_video_task, request.projectId)

    return {
        "message": "Video processing started",
        "projectId": request.projectId,
        "status": "processing",
    }
