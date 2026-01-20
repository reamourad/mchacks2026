from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from enum import Enum


class VoiceoverSource(str, Enum):
    RECORDED = "recorded"  # User recorded in browser
    UPLOADED = "uploaded"  # User uploaded audio file
    GENERATED = "generated"  # AI-generated via ElevenLabs


class Voiceover(BaseModel):
    """Voiceover embedded in project document."""
    source: VoiceoverSource
    s3_key: str
    s3_url: str
    duration: Optional[float] = None  # Duration in seconds
    text: Optional[str] = None  # Script text (only for generated)
    created_at: datetime


class VoiceoverResponse(BaseModel):
    """Response when fetching voiceover."""
    source: VoiceoverSource
    s3_url: str
    duration: Optional[float] = None
    text: Optional[str] = None
    created_at: datetime


class VoiceoverGenerate(BaseModel):
    """Request to generate voiceover from text."""
    text: str


class VoiceoverConfirm(BaseModel):
    """Confirm upload with optional metadata."""
    source: VoiceoverSource = VoiceoverSource.UPLOADED
    duration: Optional[float] = None


class VoiceoverUploadUrlResponse(BaseModel):
    """Response with presigned upload URL."""
    upload_url: str
    s3_key: str
