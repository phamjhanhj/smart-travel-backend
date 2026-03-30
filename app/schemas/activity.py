from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.location import LocationBriefOut

ActivityType = Literal["hotel", "meal", "attraction", "transport", "other"]


class ActivityCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: Optional[str] = None
    type: Optional[ActivityType] = None  # FIX 💡-1: validate enum
    location_id: Optional[UUID] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    estimated_cost: Optional[int] = Field(default=None, ge=0)
    order_index: int = 0
    booking_url: Optional[str] = None
    notes: Optional[str] = None


class ActivityUpdateRequest(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = None
    type: Optional[ActivityType] = None  # FIX 💡-1: validate enum
    location_id: Optional[UUID] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    estimated_cost: Optional[int] = Field(default=None, ge=0)
    order_index: Optional[int] = None
    booking_url: Optional[str] = None
    notes: Optional[str] = None


class ReorderItem(BaseModel):
    id: UUID
    order_index: int


class ActivityReorderRequest(BaseModel):
    day_plan_id: UUID
    items: list[ReorderItem]


class ActivityOut(BaseModel):
    id: UUID
    day_plan_id: UUID
    title: str
    description: Optional[str]
    type: Optional[ActivityType]  # FIX 💡-1: consistent với request schema
    start_time: Optional[str]
    end_time: Optional[str]
    estimated_cost: Optional[int]
    order_index: int
    booking_url: Optional[str]
    notes: Optional[str]
    location: Optional[LocationBriefOut]

    model_config = {"from_attributes": True}


class ActivityBriefOut(BaseModel):
    id: UUID
    day_plan_id: UUID
    title: str
    type: Optional[ActivityType]  # FIX 💡-1: consistent
    start_time: Optional[str]
    end_time: Optional[str]
    estimated_cost: Optional[int]
    order_index: int
    location_id: Optional[UUID]

    model_config = {"from_attributes": True}
