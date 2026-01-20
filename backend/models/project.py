from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class ProjectStatus(str, Enum):
    DRAFT = "draft"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class TimelineClip(BaseModel):
    """A clip in the project timeline - references an asset with timestamps."""
    id: str  # unique clip ID within project
    asset_id: str  # references Asset._id
    start_time: float = 0.0  # start time in source video (seconds)
    end_time: float  # end time in source video (seconds)
    order: int  # position in timeline


class ClipCreate(BaseModel):
    """Data needed to create a new clip."""
    asset_id: str
    start_time: float = 0.0
    end_time: float
    order: Optional[int] = None  # auto-assign if not provided


class ClipUpdate(BaseModel):
    """Data for updating a clip."""
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    order: Optional[int] = None


class ProjectBase(BaseModel):
    title: str = "Untitled Project"


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    title: Optional[str] = None


class ProjectInDB(ProjectBase):
    id: str = Field(alias="_id")
    user_id: Optional[str] = None  # None for anonymous projects
    session_id: Optional[str] = None  # For anonymous projects
    status: ProjectStatus = ProjectStatus.DRAFT
    clips: list[TimelineClip] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True


class ProjectResponse(ProjectBase):
    id: str
    user_id: Optional[str] = None
    status: ProjectStatus
    clips: list[TimelineClip] = []
    created_at: datetime
    updated_at: datetime
