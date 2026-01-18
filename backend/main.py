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
from video_processing import process_video_with_creatomate
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
    Creates a final video from Gumloop matches using the Creatomate API.
    """
    # Assuming the original S3 URLs are needed by Creatomate
    # For now, we're just mapping the matched_clip names to dummy S3 URLs for demonstration.
    # In a real scenario, you'd fetch the actual S3 URLs associated with these clip names.
    source_s3_urls = {match["matched_clip"]: f"https://your-s3-bucket.s3.amazonaws.com/{match['matched_clip']}"
                      for match in request.matches if "matched_clip" in match}

    try:
        # Process video with Creatomate
        final_video_url = await process_video_with_creatomate(
            request.matches,
            request.username,
            request.projectName,
            source_s3_urls
        )

        print(f"Video created successfully by Creatomate: {final_video_url}")

        return {
            "success": True,
            "videoUrl": final_video_url,
            # Creatomate directly provides the final URL, S3 key might not be applicable here
            # or would be part of Creatomate's internal storage.
            "s3Key": None, 
            "clipsProcessed": len(request.matches),
        }

    except Exception as e:
        print(f"Error creating video with Creatomate: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Removed process_video_task and find_clip_s3_key as they are no longer used.
