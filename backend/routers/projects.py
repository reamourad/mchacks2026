import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import APIRouter, Depends, HTTPException, status, Request
from typing import Optional
from datetime import datetime
from bson import ObjectId

from database import get_database
from models import ProjectCreate, ProjectUpdate, ProjectResponse, ProjectStatus
from middleware import get_current_user, get_session_id, User

router = APIRouter(prefix="/projects", tags=["projects"])


def project_to_response(project: dict) -> ProjectResponse:
    """Convert MongoDB document to ProjectResponse."""
    return ProjectResponse(
        id=str(project["_id"]),
        title=project.get("title", "Untitled Project"),
        user_id=project.get("user_id"),
        status=project.get("status", ProjectStatus.DRAFT),
        clips=project.get("clips", []),
        created_at=project.get("created_at", datetime.utcnow()),
        updated_at=project.get("updated_at", datetime.utcnow()),
    )


@router.get("", response_model=list[ProjectResponse])
async def list_projects(
    request: Request,
    user: Optional[User] = Depends(get_current_user),
):
    """
    List all projects for the current user.
    - Authenticated: returns user's saved projects
    - Anonymous: returns projects for current session
    """
    db = get_database()

    if user:
        # Authenticated user - get their projects
        cursor = db.projects.find({"user_id": user.user_id}).sort("updated_at", -1)
    else:
        # Anonymous user - get session projects
        session_id = get_session_id(request)
        cursor = db.projects.find({"session_id": session_id, "user_id": None}).sort(
            "updated_at", -1
        )

    projects = await cursor.to_list(length=100)
    return [project_to_response(p) for p in projects]


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    request: Request,
    project_data: ProjectCreate,
    user: Optional[User] = Depends(get_current_user),
):
    """
    Create a new project.
    - Authenticated: creates project with user_id (title must be unique)
    - Anonymous: creates project with session_id
    """
    db = get_database()
    session_id = get_session_id(request)

    # Check for duplicate title only for authenticated users
    if user:
        existing = await db.projects.find_one({
            "user_id": user.user_id,
            "title": project_data.title,
        })
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A project with this title already exists"
            )

    now = datetime.utcnow()
    project = {
        "title": project_data.title,
        "user_id": user.user_id if user else None,
        "session_id": session_id if not user else None,
        "status": ProjectStatus.DRAFT,
        "clips": [],
        "created_at": now,
        "updated_at": now,
    }

    result = await db.projects.insert_one(project)
    project["_id"] = result.inserted_id

    return project_to_response(project)


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    request: Request,
    user: Optional[User] = Depends(get_current_user),
):
    """Get a specific project by ID."""
    db = get_database()

    try:
        object_id = ObjectId(project_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid project ID")

    project = await db.projects.find_one({"_id": object_id})

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Check access permission
    session_id = get_session_id(request)
    has_access = False

    if user and project.get("user_id") == user.user_id:
        has_access = True
    elif not project.get("user_id") and project.get("session_id") == session_id:
        has_access = True

    if not has_access:
        raise HTTPException(status_code=403, detail="Access denied")

    return project_to_response(project)


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    project_data: ProjectUpdate,
    request: Request,
    user: Optional[User] = Depends(get_current_user),
):
    """Update project metadata (title, description)."""
    db = get_database()

    try:
        object_id = ObjectId(project_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid project ID")

    project = await db.projects.find_one({"_id": object_id})

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Check access permission
    session_id = get_session_id(request)
    has_access = False

    if user and project.get("user_id") == user.user_id:
        has_access = True
    elif not project.get("user_id") and project.get("session_id") == session_id:
        has_access = True

    if not has_access:
        raise HTTPException(status_code=403, detail="Access denied")

    # Check for duplicate title if updating title for authenticated user
    if project_data.title is not None and user:
        existing = await db.projects.find_one({
            "user_id": user.user_id,
            "title": project_data.title,
            "_id": {"$ne": object_id},  # Exclude current project
        })
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A project with this title already exists"
            )

    # Build update dict
    update_data = {"updated_at": datetime.utcnow()}
    if project_data.title is not None:
        update_data["title"] = project_data.title

    await db.projects.update_one({"_id": object_id}, {"$set": update_data})

    updated_project = await db.projects.find_one({"_id": object_id})
    return project_to_response(updated_project)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: str,
    request: Request,
    user: Optional[User] = Depends(get_current_user),
):
    """Delete a project."""
    db = get_database()

    try:
        object_id = ObjectId(project_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid project ID")

    project = await db.projects.find_one({"_id": object_id})

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Check access permission
    session_id = get_session_id(request)
    has_access = False

    if user and project.get("user_id") == user.user_id:
        has_access = True
    elif not project.get("user_id") and project.get("session_id") == session_id:
        has_access = True

    if not has_access:
        raise HTTPException(status_code=403, detail="Access denied")

    # TODO: Also delete clips from S3

    await db.projects.delete_one({"_id": object_id})


@router.post("/{project_id}/claim", response_model=ProjectResponse)
async def claim_project(
    project_id: str,
    request: Request,
    user: User = Depends(get_current_user),
):
    """
    Claim an anonymous project for the authenticated user.
    This is called when user clicks "Save" on an anonymous project.
    """
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required to claim project")

    db = get_database()

    try:
        object_id = ObjectId(project_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid project ID")

    session_id = get_session_id(request)

    # Find the anonymous project belonging to this session
    project = await db.projects.find_one({
        "_id": object_id,
        "session_id": session_id,
        "user_id": None,
    })

    if not project:
        raise HTTPException(
            status_code=404,
            detail="Project not found or already claimed"
        )

    # Claim the project
    await db.projects.update_one(
        {"_id": object_id},
        {
            "$set": {
                "user_id": user.user_id,
                "session_id": None,
                "updated_at": datetime.utcnow(),
            }
        }
    )

    updated_project = await db.projects.find_one({"_id": object_id})
    return project_to_response(updated_project)
