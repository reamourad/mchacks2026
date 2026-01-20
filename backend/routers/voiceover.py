import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import APIRouter, Depends, HTTPException, status, Request, UploadFile, File
from typing import Optional
from datetime import datetime
from bson import ObjectId

from database import get_database
from models import (
    VoiceoverSource,
    VoiceoverResponse,
    VoiceoverGenerate,
    VoiceoverConfirm,
    VoiceoverUploadUrlResponse,
)
from middleware import get_current_user, get_session_id, User
from services.s3 import generate_presigned_upload_url, upload_file, delete_file, get_s3_url
from services.elevenlabs import generate_speech

router = APIRouter(prefix="/projects/{project_id}/voiceover", tags=["voiceover"])


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


def get_voiceover_s3_prefix(project_id: str, user: Optional[User], session_id: str) -> str:
    """Get S3 prefix for voiceover storage."""
    if user:
        return f"users/{user.user_id}/{project_id}/voiceover"
    else:
        return f"anonymous/{session_id}/{project_id}/voiceover"


@router.get("", response_model=Optional[VoiceoverResponse])
async def get_voiceover(
    project_id: str,
    request: Request,
    user: Optional[User] = Depends(get_current_user),
):
    """Get the current voiceover for this project."""
    project = await verify_project_access(project_id, request, user)

    voiceover = project.get("voiceover")
    if not voiceover:
        return None

    return VoiceoverResponse(
        source=voiceover["source"],
        s3_url=voiceover["s3_url"],
        duration=voiceover.get("duration"),
        text=voiceover.get("text"),
        created_at=voiceover["created_at"],
    )


@router.post("/upload-url", response_model=VoiceoverUploadUrlResponse)
async def get_upload_url(
    project_id: str,
    request: Request,
    user: Optional[User] = Depends(get_current_user),
):
    """
    Get a presigned URL for uploading a voiceover (recorded or file upload).
    """
    await verify_project_access(project_id, request, user)

    session_id = get_session_id(request)
    s3_prefix = get_voiceover_s3_prefix(project_id, user, session_id)

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    s3_key = f"{s3_prefix}/{timestamp}_voiceover.mp3"

    upload_url = await generate_presigned_upload_url(
        s3_key=s3_key,
        content_type="audio/mpeg",
        expiration=3600,
    )

    if not upload_url:
        raise HTTPException(status_code=500, detail="Failed to generate upload URL")

    return VoiceoverUploadUrlResponse(
        upload_url=upload_url,
        s3_key=s3_key,
    )


@router.post("/upload", response_model=VoiceoverResponse)
async def upload_voiceover_direct(
    project_id: str,
    request: Request,
    file: UploadFile = File(...),
    user: Optional[User] = Depends(get_current_user),
):
    """
    Direct upload endpoint for voiceover files.
    Accepts the file directly and uploads to S3 from the backend.
    """
    project = await verify_project_access(project_id, request, user)
    db = get_database()

    # Read file content
    file_content = await file.read()

    # Delete old voiceover from S3 if exists
    old_voiceover = project.get("voiceover")
    if old_voiceover:
        await delete_file(old_voiceover["s3_key"])

    # Build S3 key
    session_id = get_session_id(request)
    s3_prefix = get_voiceover_s3_prefix(project_id, user, session_id)
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

    # Get file extension from original filename
    ext = Path(file.filename).suffix if file.filename else ".m4a"
    s3_key = f"{s3_prefix}/{timestamp}_voiceover{ext}"

    # Upload to S3
    content_type = file.content_type or "audio/mp4"
    s3_url = await upload_file(
        file_content=file_content,
        s3_key=s3_key,
        content_type=content_type,
    )

    if not s3_url:
        raise HTTPException(status_code=500, detail="Failed to upload voiceover to S3")

    now = datetime.utcnow()
    voiceover = {
        "source": VoiceoverSource.UPLOADED,
        "s3_key": s3_key,
        "s3_url": s3_url,
        "duration": None,
        "text": None,
        "created_at": now,
    }

    print(f"[Voiceover Upload] Saving voiceover to project {project_id}")
    print(f"[Voiceover Upload] s3_key: {s3_key}")

    result = await db.projects.update_one(
        {"_id": ObjectId(project_id)},
        {
            "$set": {
                "voiceover": voiceover,
                "updated_at": now,
            }
        }
    )
    print(f"[Voiceover Upload] Update result - matched: {result.matched_count}, modified: {result.modified_count}")

    return VoiceoverResponse(
        source=voiceover["source"],
        s3_url=voiceover["s3_url"],
        duration=voiceover.get("duration"),
        text=voiceover.get("text"),
        created_at=voiceover["created_at"],
    )


@router.post("/confirm", response_model=VoiceoverResponse)
async def confirm_upload(
    project_id: str,
    s3_key: str,
    request: Request,
    confirm_data: Optional[VoiceoverConfirm] = None,
    user: Optional[User] = Depends(get_current_user),
):
    """
    Confirm that a voiceover has been uploaded to S3.
    Replaces any existing voiceover.
    """
    project = await verify_project_access(project_id, request, user)
    db = get_database()

    # Delete old voiceover from S3 if exists
    old_voiceover = project.get("voiceover")
    if old_voiceover:
        await delete_file(old_voiceover["s3_key"])

    now = datetime.utcnow()
    source = confirm_data.source if confirm_data else VoiceoverSource.UPLOADED

    voiceover = {
        "source": source,
        "s3_key": s3_key,
        "s3_url": get_s3_url(s3_key),
        "duration": confirm_data.duration if confirm_data else None,
        "text": None,
        "created_at": now,
    }

    await db.projects.update_one(
        {"_id": ObjectId(project_id)},
        {
            "$set": {
                "voiceover": voiceover,
                "updated_at": now,
            }
        }
    )

    return VoiceoverResponse(
        source=voiceover["source"],
        s3_url=voiceover["s3_url"],
        duration=voiceover.get("duration"),
        text=voiceover.get("text"),
        created_at=voiceover["created_at"],
    )


@router.post("/generate", response_model=VoiceoverResponse)
async def generate_voiceover(
    project_id: str,
    generate_data: VoiceoverGenerate,
    request: Request,
    user: Optional[User] = Depends(get_current_user),
):
    """
    Generate a voiceover from text using ElevenLabs.
    Replaces any existing voiceover.
    """
    project = await verify_project_access(project_id, request, user)
    db = get_database()

    if not generate_data.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    # Generate speech with ElevenLabs
    audio_bytes = await generate_speech(generate_data.text)

    if not audio_bytes:
        raise HTTPException(
            status_code=500,
            detail="Failed to generate voiceover. Check ElevenLabs configuration."
        )

    # Delete old voiceover from S3 if exists
    old_voiceover = project.get("voiceover")
    if old_voiceover:
        await delete_file(old_voiceover["s3_key"])

    # Upload to S3
    session_id = get_session_id(request)
    s3_prefix = get_voiceover_s3_prefix(project_id, user, session_id)
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    s3_key = f"{s3_prefix}/{timestamp}_generated.mp3"

    s3_url = await upload_file(
        file_content=audio_bytes,
        s3_key=s3_key,
        content_type="audio/mpeg",
    )

    if not s3_url:
        raise HTTPException(status_code=500, detail="Failed to upload voiceover to S3")

    now = datetime.utcnow()
    voiceover = {
        "source": VoiceoverSource.GENERATED,
        "s3_key": s3_key,
        "s3_url": s3_url,
        "duration": None,  # Could calculate from audio bytes if needed
        "text": generate_data.text,
        "created_at": now,
    }

    await db.projects.update_one(
        {"_id": ObjectId(project_id)},
        {
            "$set": {
                "voiceover": voiceover,
                "updated_at": now,
            }
        }
    )

    return VoiceoverResponse(
        source=voiceover["source"],
        s3_url=voiceover["s3_url"],
        duration=voiceover.get("duration"),
        text=voiceover.get("text"),
        created_at=voiceover["created_at"],
    )


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def delete_voiceover(
    project_id: str,
    request: Request,
    user: Optional[User] = Depends(get_current_user),
):
    """Delete the voiceover from this project."""
    project = await verify_project_access(project_id, request, user)
    db = get_database()

    voiceover = project.get("voiceover")
    if not voiceover:
        raise HTTPException(status_code=404, detail="No voiceover found")

    # Delete from S3
    await delete_file(voiceover["s3_key"])

    # Remove from project
    await db.projects.update_one(
        {"_id": ObjectId(project_id)},
        {
            "$unset": {"voiceover": ""},
            "$set": {"updated_at": datetime.utcnow()},
        }
    )
