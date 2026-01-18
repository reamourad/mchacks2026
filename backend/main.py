import os
import tempfile
import shutil
import asyncio
import httpx
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
from s3 import download_from_s3, upload_file_to_s3, generate_final_video_key, get_s3_url
from video_processing import create_video_from_matches, create_merged_video
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
async def create_video_endpoint(request: CreateVideoRequest):
    """
    Creates a final video from Gumloop matches using Creatomate for processing.
    """
    try:
        print(f"Creating video for {request.username}/{request.projectName} with {len(request.matches)} matches using Creatomate.")

        # Use Creatomate to merge clips
        creatomate_url = await create_video_from_matches(request.matches, get_s3_url)

        print(f"Creatomate render complete: {creatomate_url}")

        # Download from Creatomate and re-upload to our S3
        temp_dir = tempfile.mkdtemp(prefix=f"xpresso-{request.username}-{request.projectName}-")
        try:
            local_video_path = os.path.join(temp_dir, "final_video.mp4")

            print(f"Downloading rendered video from Creatomate...")
            async with httpx.AsyncClient(timeout=300) as client:
                async with client.stream("GET", creatomate_url, follow_redirects=True) as response:
                    response.raise_for_status()
                    with open(local_video_path, "wb") as f:
                        async for chunk in response.aiter_bytes():
                            f.write(chunk)

            print(f"Uploading to S3...")
            final_s3_key = generate_final_video_key(request.username, request.projectName)
            final_video_url = upload_file_to_s3(local_video_path, final_s3_key)

            print(f"Video created successfully: {final_video_url}")

            return {
                "success": True,
                "videoUrl": final_video_url,
                "s3Key": final_s3_key,
                "clipsProcessed": len(request.matches),
                "creatomateUrl": creatomate_url,  # Also return this in case S3 upload fails
            }
        finally:
            print(f"Cleaning up temp directory: {temp_dir}")
            shutil.rmtree(temp_dir)

    except Exception as e:
        print(f"Error creating video with Creatomate: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/create_video_direct")
async def create_video_direct_endpoint(request: CreateVideoRequest):
    """
    Creates a final video and returns the Creatomate URL directly (without S3 re-upload).
    Useful for faster response when S3 storage isn't needed.
    """
    try:
        print(f"Creating video for {request.username}/{request.projectName} with {len(request.matches)} matches.")

        creatomate_url = await create_video_from_matches(request.matches, get_s3_url)

        return {
            "success": True,
            "videoUrl": creatomate_url,
            "clipsProcessed": len(request.matches),
        }

    except Exception as e:
        print(f"Error creating video with Creatomate: {e}")
        raise HTTPException(status_code=500, detail=str(e))