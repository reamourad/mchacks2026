from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class AssetStatus(str, Enum):
    PENDING = "pending"  # Upload URL generated, waiting for upload
    READY = "ready"      # Upload confirmed
    FAILED = "failed"    # Upload failed or timed out


class AssetType(str, Enum):
    VIDEO = "video"
    AUDIO = "audio"
    IMAGE = "image"


class AssetCreate(BaseModel):
    filename: str
    content_type: str = "video/mp4"


class AssetResponse(BaseModel):
    id: str
    project_id: str
    filename: str
    s3_key: str
    s3_url: Optional[str] = None
    content_type: str
    size_bytes: Optional[int] = None
    duration: Optional[float] = None  # Duration in seconds (for video/audio)
    asset_type: AssetType = AssetType.VIDEO
    status: AssetStatus
    order: int = 0
    created_at: datetime
    updated_at: datetime


class AssetConfirm(BaseModel):
    """Optional data when confirming upload."""
    duration: Optional[float] = None  # Frontend can provide duration after reading video
    size_bytes: Optional[int] = None


class UploadUrlResponse(BaseModel):
    asset_id: str
    upload_url: str
    s3_key: str
