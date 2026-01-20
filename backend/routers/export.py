import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import os
import tempfile
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from typing import Optional
from bson import ObjectId

from database import get_database
from middleware import get_current_user, get_session_id, User
from services.s3 import s3_service
from services.video_processing import process_project_export
from services.transcription import transcribe_audio

router = APIRouter(prefix="/projects/{project_id}/export", tags=["export"])


class ExportRequest(BaseModel):
    """Request body for export - transcript data for subtitles."""
    transcript: list[dict] = []  # [{start, end, text, emotion}, ...]


class ExportResponse(BaseModel):
    """Response with the exported video URL."""
    export_id: str
    video_url: str
    created_at: datetime


class ExportStatusResponse(BaseModel):
    """Response for export status check."""
    export_id: str
    status: str  # pending, processing, completed, failed
    video_url: Optional[str] = None
    error: Optional[str] = None


async def verify_project_access(
    project_id: str,
    request: Request,
    user: Optional[User],
) -> dict:
    """Verify user has access to the project. Returns project if accessible."""
    db = get_database()

    try:
        object_id = ObjectId(project_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid project ID")

    project = await db.projects.find_one({"_id": object_id})

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    session_id = get_session_id(request)
    has_access = False

    if user and project.get("user_id") == user.user_id:
        has_access = True
    elif not project.get("user_id") and project.get("session_id") == session_id:
        has_access = True

    if not has_access:
        raise HTTPException(status_code=403, detail="Access denied")

    return project


@router.post("", response_model=ExportResponse)
async def export_project(
    project_id: str,
    export_request: ExportRequest,
    request: Request,
    user: Optional[User] = Depends(get_current_user),
):
    """
    Export project video with subtitles.

    Pipeline:
    1. Get project clips from database
    2. Download clips from S3 to temp directory
    3. Merge clips and add subtitles
    4. Upload result to S3
    5. Return video URL
    """
    project = await verify_project_access(project_id, request, user)
    db = get_database()

    clips = project.get("clips", [])
    if not clips:
        raise HTTPException(status_code=400, detail="No clips in project")

    # Sort clips by order
    clips = sorted(clips, key=lambda c: c.get("order", 0))

    # Get asset info for each clip
    asset_ids = [clip["asset_id"] for clip in clips]
    assets = await db.assets.find(
        {"_id": {"$in": [ObjectId(aid) for aid in asset_ids]}}
    ).to_list(None)

    asset_map = {str(a["_id"]): a for a in assets}

    # Create temp directory for processing (ignore cleanup errors on Windows)
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
        clip_paths = []

        # Download each clip from S3
        for i, clip in enumerate(clips):
            asset = asset_map.get(clip["asset_id"])
            if not asset:
                raise HTTPException(
                    status_code=400,
                    detail=f"Asset not found for clip {clip['id']}"
                )

            s3_key = asset["s3_key"]
            local_path = os.path.join(temp_dir, f"clip_{i}.mp4")

            # Download from S3
            success = await s3_service.download_file(s3_key, local_path)
            if not success:
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to download clip {clip['id']}"
                )

            clip_paths.append(local_path)

        # Check for voiceover audio (from project document)
        audio_path = None
        voiceover = project.get("voiceover")
        print(f"[Export] Project voiceover data: {voiceover}")
        if voiceover and voiceover.get("s3_key"):
            audio_path = os.path.join(temp_dir, "voiceover.m4a")
            print(f"[Export] Downloading voiceover from S3: {voiceover['s3_key']}")
            success = await s3_service.download_file(voiceover["s3_key"], audio_path)
            if not success:
                print("[Export] Failed to download voiceover from S3")
                audio_path = None  # Continue without audio if download fails
            else:
                print(f"[Export] Voiceover downloaded to: {audio_path}")
        else:
            print("[Export] No voiceover found in project")

        # Auto-transcribe if no transcript provided but voiceover exists
        transcript_data = export_request.transcript
        if not transcript_data and audio_path:
            print("No transcript provided, auto-transcribing voiceover...")
            transcript_data = await transcribe_audio(audio_path)
            if transcript_data:
                print(f"Transcription complete: {len(transcript_data)} segments")
            else:
                print("Transcription failed, proceeding without subtitles")
                transcript_data = []

        # Generate output path
        export_id = str(uuid.uuid4())
        output_filename = f"export_{export_id}.mp4"
        output_path = os.path.join(temp_dir, output_filename)

        # Process video
        try:
            await process_project_export(
                clip_paths=clip_paths,
                transcript_data=transcript_data,
                output_path=output_path,
                audio_path=audio_path,
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Video processing failed: {str(e)}"
            )

        # Upload to S3
        s3_key = f"exports/{project_id}/{output_filename}"
        upload_success = await s3_service.upload_file(output_path, s3_key)
        if not upload_success:
            raise HTTPException(
                status_code=500,
                detail="Failed to upload exported video"
            )

        # Get URL for the exported video
        video_url = await s3_service.get_download_url(s3_key)

        # Store export record
        export_record = {
            "export_id": export_id,
            "project_id": project_id,
            "s3_key": s3_key,
            "status": "completed",
            "created_at": datetime.utcnow(),
        }
        await db.exports.insert_one(export_record)

        return ExportResponse(
            export_id=export_id,
            video_url=video_url,
            created_at=export_record["created_at"],
        )


@router.get("/history")
async def get_export_history(
    project_id: str,
    request: Request,
    user: Optional[User] = Depends(get_current_user),
):
    """Get list of previous exports for a project."""
    await verify_project_access(project_id, request, user)
    db = get_database()

    exports = await db.exports.find(
        {"project_id": project_id}
    ).sort("created_at", -1).to_list(20)

    result = []
    for exp in exports:
        video_url = await s3_service.get_download_url(exp["s3_key"])
        result.append({
            "export_id": exp["export_id"],
            "status": exp.get("status", "completed"),
            "video_url": video_url,
            "created_at": exp["created_at"],
        })

    return result
