import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import APIRouter, Depends, HTTPException, status, Request, UploadFile, File
from typing import Optional
from datetime import datetime
from bson import ObjectId

from database import get_database
from models import AssetCreate, AssetResponse, AssetConfirm, AssetStatus, AssetType, UploadUrlResponse
from middleware import get_current_user, get_session_id, User
from services.s3 import generate_presigned_upload_url, delete_file, get_s3_url, upload_file

router = APIRouter(prefix="/projects/{project_id}/assets", tags=["assets"])


def get_asset_type(content_type: str) -> AssetType:
    """Determine asset type from content type."""
    if content_type.startswith("video/"):
        return AssetType.VIDEO
    elif content_type.startswith("audio/"):
        return AssetType.AUDIO
    elif content_type.startswith("image/"):
        return AssetType.IMAGE
    return AssetType.VIDEO


def asset_to_response(asset: dict) -> AssetResponse:
    """Convert MongoDB document to AssetResponse."""
    return AssetResponse(
        id=str(asset["_id"]),
        project_id=str(asset["project_id"]),
        filename=asset["filename"],
        s3_key=asset["s3_key"],
        s3_url=asset.get("s3_url"),
        content_type=asset["content_type"],
        size_bytes=asset.get("size_bytes"),
        duration=asset.get("duration"),
        asset_type=asset.get("asset_type", AssetType.VIDEO),
        status=asset.get("status", AssetStatus.PENDING),
        order=asset.get("order", 0),
        created_at=asset.get("created_at", datetime.utcnow()),
        updated_at=asset.get("updated_at", datetime.utcnow()),
    )


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


@router.post("/upload-url", response_model=UploadUrlResponse)
async def get_upload_url(
    project_id: str,
    asset_data: AssetCreate,
    request: Request,
    user: Optional[User] = Depends(get_current_user),
):
    """
    Generate a presigned URL for direct S3 upload.
    Creates a pending asset record in the database.
    """
    project = await verify_project_access(project_id, request, user)
    db = get_database()

    # Build S3 key path
    if user:
        s3_prefix = f"users/{user.user_id}/{project_id}"
    else:
        session_id = get_session_id(request)
        s3_prefix = f"anonymous/{session_id}/{project_id}"

    # Get next asset order number
    asset_count = await db.assets.count_documents({"project_id": ObjectId(project_id)})

    # Generate unique filename
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    safe_filename = asset_data.filename.replace(" ", "_")
    s3_key = f"{s3_prefix}/{timestamp}_{safe_filename}"

    # Create pending asset record
    now = datetime.utcnow()
    asset = {
        "project_id": ObjectId(project_id),
        "filename": asset_data.filename,
        "s3_key": s3_key,
        "content_type": asset_data.content_type,
        "asset_type": get_asset_type(asset_data.content_type),
        "status": AssetStatus.PENDING,
        "order": asset_count + 1,
        "created_at": now,
        "updated_at": now,
    }

    result = await db.assets.insert_one(asset)
    asset_id = str(result.inserted_id)

    # Generate presigned upload URL
    upload_url = await generate_presigned_upload_url(
        s3_key=s3_key,
        content_type=asset_data.content_type,
        expiration=3600,  # 1 hour
    )

    if not upload_url:
        # Clean up the asset record if URL generation failed
        await db.assets.delete_one({"_id": result.inserted_id})
        raise HTTPException(
            status_code=500,
            detail="Failed to generate upload URL"
        )

    return UploadUrlResponse(
        asset_id=asset_id,
        upload_url=upload_url,
        s3_key=s3_key,
    )


@router.post("/{asset_id}/confirm", response_model=AssetResponse)
async def confirm_upload(
    project_id: str,
    asset_id: str,
    request: Request,
    confirm_data: Optional[AssetConfirm] = None,
    user: Optional[User] = Depends(get_current_user),
):
    """
    Confirm that an asset has been uploaded to S3.
    Marks the asset as ready.
    Optionally accepts duration and size_bytes from the frontend.
    """
    await verify_project_access(project_id, request, user)
    db = get_database()

    try:
        asset_object_id = ObjectId(asset_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid asset ID")

    asset = await db.assets.find_one({
        "_id": asset_object_id,
        "project_id": ObjectId(project_id),
    })

    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    if asset["status"] == AssetStatus.READY:
        return asset_to_response(asset)

    # Update asset status and generate public URL
    s3_url = get_s3_url(asset["s3_key"])

    update_data = {
        "status": AssetStatus.READY,
        "s3_url": s3_url,
        "updated_at": datetime.utcnow(),
    }

    # Add optional metadata from frontend
    if confirm_data:
        if confirm_data.duration is not None:
            update_data["duration"] = confirm_data.duration
        if confirm_data.size_bytes is not None:
            update_data["size_bytes"] = confirm_data.size_bytes

    await db.assets.update_one(
        {"_id": asset_object_id},
        {"$set": update_data}
    )

    updated_asset = await db.assets.find_one({"_id": asset_object_id})
    return asset_to_response(updated_asset)


@router.get("", response_model=list[AssetResponse])
async def list_assets(
    project_id: str,
    request: Request,
    user: Optional[User] = Depends(get_current_user),
):
    """List all assets for a project."""
    await verify_project_access(project_id, request, user)
    db = get_database()

    cursor = db.assets.find({
        "project_id": ObjectId(project_id),
        "status": AssetStatus.READY,  # Only return confirmed uploads
    }).sort("order", 1)

    assets = await cursor.to_list(length=100)
    return [asset_to_response(a) for a in assets]


@router.delete("/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_asset(
    project_id: str,
    asset_id: str,
    request: Request,
    user: Optional[User] = Depends(get_current_user),
):
    """Delete an asset from S3 and MongoDB."""
    await verify_project_access(project_id, request, user)
    db = get_database()

    try:
        asset_object_id = ObjectId(asset_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid asset ID")

    asset = await db.assets.find_one({
        "_id": asset_object_id,
        "project_id": ObjectId(project_id),
    })

    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    # Delete from S3
    await delete_file(asset["s3_key"])

    # Delete from MongoDB
    await db.assets.delete_one({"_id": asset_object_id})
