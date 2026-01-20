import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import APIRouter, Depends, HTTPException, status, Request
from typing import Optional
from datetime import datetime
from bson import ObjectId
import uuid

from database import get_database
from models import TimelineClip, ClipCreate, ClipUpdate
from middleware import get_current_user, get_session_id, User

router = APIRouter(prefix="/projects/{project_id}/clips", tags=["clips"])


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


async def verify_asset_exists(asset_id: str, project_id: str) -> dict:
    """Verify the asset exists and belongs to the project."""
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
        raise HTTPException(status_code=404, detail="Asset not found in this project")

    return asset


@router.get("", response_model=list[TimelineClip])
async def list_clips(
    project_id: str,
    request: Request,
    user: Optional[User] = Depends(get_current_user),
):
    """Get all clips in the project timeline, ordered by position."""
    project = await verify_project_access(project_id, request, user)
    clips = project.get("clips", [])
    # Sort by order
    clips.sort(key=lambda c: c.get("order", 0))
    return clips


@router.post("", response_model=TimelineClip, status_code=status.HTTP_201_CREATED)
async def add_clip(
    project_id: str,
    clip_data: ClipCreate,
    request: Request,
    user: Optional[User] = Depends(get_current_user),
):
    """Add a new clip to the project timeline."""
    project = await verify_project_access(project_id, request, user)

    # Verify the asset exists
    asset = await verify_asset_exists(clip_data.asset_id, project_id)

    # Validate timestamps
    if clip_data.start_time < 0:
        raise HTTPException(status_code=400, detail="start_time cannot be negative")
    if clip_data.end_time <= clip_data.start_time:
        raise HTTPException(status_code=400, detail="end_time must be greater than start_time")

    # If asset has duration, validate end_time doesn't exceed it
    if asset.get("duration") and clip_data.end_time > asset["duration"]:
        raise HTTPException(
            status_code=400,
            detail=f"end_time exceeds asset duration ({asset['duration']}s)"
        )

    db = get_database()
    clips = project.get("clips", [])

    # Determine order
    if clip_data.order is not None:
        order = clip_data.order
    else:
        # Auto-assign to end of timeline
        order = max([c.get("order", 0) for c in clips], default=0) + 1

    # Create clip
    new_clip = {
        "id": str(uuid.uuid4()),
        "asset_id": clip_data.asset_id,
        "start_time": clip_data.start_time,
        "end_time": clip_data.end_time,
        "order": order,
    }

    # Add to project
    await db.projects.update_one(
        {"_id": ObjectId(project_id)},
        {
            "$push": {"clips": new_clip},
            "$set": {"updated_at": datetime.utcnow()},
        }
    )

    return TimelineClip(**new_clip)


@router.patch("/{clip_id}", response_model=TimelineClip)
async def update_clip(
    project_id: str,
    clip_id: str,
    clip_data: ClipUpdate,
    request: Request,
    user: Optional[User] = Depends(get_current_user),
):
    """Update a clip's timestamps or order."""
    project = await verify_project_access(project_id, request, user)

    clips = project.get("clips", [])
    clip_index = next((i for i, c in enumerate(clips) if c.get("id") == clip_id), None)

    if clip_index is None:
        raise HTTPException(status_code=404, detail="Clip not found")

    clip = clips[clip_index]

    # Build update
    update_fields = {}
    if clip_data.start_time is not None:
        if clip_data.start_time < 0:
            raise HTTPException(status_code=400, detail="start_time cannot be negative")
        update_fields["clips.$.start_time"] = clip_data.start_time
        clip["start_time"] = clip_data.start_time

    if clip_data.end_time is not None:
        update_fields["clips.$.end_time"] = clip_data.end_time
        clip["end_time"] = clip_data.end_time

    if clip_data.order is not None:
        update_fields["clips.$.order"] = clip_data.order
        clip["order"] = clip_data.order

    # Validate timestamps
    if clip["end_time"] <= clip["start_time"]:
        raise HTTPException(status_code=400, detail="end_time must be greater than start_time")

    if not update_fields:
        return TimelineClip(**clip)

    update_fields["updated_at"] = datetime.utcnow()

    db = get_database()
    await db.projects.update_one(
        {"_id": ObjectId(project_id), "clips.id": clip_id},
        {"$set": update_fields}
    )

    return TimelineClip(**clip)


@router.delete("/{clip_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_clip(
    project_id: str,
    clip_id: str,
    request: Request,
    user: Optional[User] = Depends(get_current_user),
):
    """Remove a clip from the timeline."""
    project = await verify_project_access(project_id, request, user)

    clips = project.get("clips", [])
    clip_exists = any(c.get("id") == clip_id for c in clips)

    if not clip_exists:
        raise HTTPException(status_code=404, detail="Clip not found")

    db = get_database()
    await db.projects.update_one(
        {"_id": ObjectId(project_id)},
        {
            "$pull": {"clips": {"id": clip_id}},
            "$set": {"updated_at": datetime.utcnow()},
        }
    )


@router.put("/reorder", response_model=list[TimelineClip])
async def reorder_clips(
    project_id: str,
    clip_ids: list[str],
    request: Request,
    user: Optional[User] = Depends(get_current_user),
):
    """
    Reorder all clips in the timeline.
    Pass an array of clip IDs in the desired order.
    """
    project = await verify_project_access(project_id, request, user)

    clips = project.get("clips", [])
    clip_map = {c["id"]: c for c in clips}

    # Validate all clip IDs exist
    for clip_id in clip_ids:
        if clip_id not in clip_map:
            raise HTTPException(status_code=400, detail=f"Clip {clip_id} not found")

    # Check no clips are missing
    if set(clip_ids) != set(clip_map.keys()):
        raise HTTPException(status_code=400, detail="clip_ids must include all clips")

    # Update order
    reordered_clips = []
    for i, clip_id in enumerate(clip_ids):
        clip = clip_map[clip_id]
        clip["order"] = i + 1
        reordered_clips.append(clip)

    db = get_database()
    await db.projects.update_one(
        {"_id": ObjectId(project_id)},
        {
            "$set": {
                "clips": reordered_clips,
                "updated_at": datetime.utcnow(),
            }
        }
    )

    return [TimelineClip(**c) for c in reordered_clips]
