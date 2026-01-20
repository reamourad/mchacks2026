from pydantic import BaseModel
from typing import Optional


class TimelineClip(BaseModel):
    """A clip on the project timeline."""
    id: str
    asset_id: str
    start_time: float = 0.0  # Start time in the source asset (seconds)
    end_time: float  # End time in the source asset (seconds)
    order: int = 0  # Position in timeline


class ClipCreate(BaseModel):
    """Request to add a clip to the timeline."""
    asset_id: str
    start_time: float = 0.0
    end_time: float
    order: Optional[int] = None  # Auto-assign if not provided


class ClipUpdate(BaseModel):
    """Request to update a clip's properties."""
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    order: Optional[int] = None
