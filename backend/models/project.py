from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class ProjectStatus(str, Enum):
    DRAFT = "draft"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Clip(BaseModel):
    clip_number: int
    filename: str
    s3_key: str
    s3_url: str
    duration: Optional[float] = None
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)


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
    clips: list[Clip] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True


class ProjectResponse(ProjectBase):
    id: str
    user_id: Optional[str] = None
    status: ProjectStatus
    clips: list[Clip] = []
    created_at: datetime
    updated_at: datetime
