from datetime import datetime
from typing import Generic, List, Optional, TypeVar

from pydantic import BaseModel, ConfigDict, Field


class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=20, ge=1, le=100)


class PaginatedResponse(BaseModel):
    total: int
    page: int
    per_page: int
    pages: int


T = TypeVar("T")


class PaginatedData(PaginatedResponse, Generic[T]):
    items: List[T]


class TimestampMixin(BaseModel):
    created_at: datetime
    updated_at: Optional[datetime] = None


class LocationBase(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    accuracy: Optional[float] = Field(default=None, ge=0)
    altitude: Optional[float] = None


class SuccessResponse(BaseModel):
    success: bool = True
    message: str


class ErrorDetail(BaseModel):
    field: Optional[str] = None
    message: str


class ErrorResponse(BaseModel):
    success: bool = False
    error_code: str
    message: str
    details: Optional[List[ErrorDetail]] = None


class OfflineSyncMixin(BaseModel):
    client_created_at: Optional[datetime] = None
    offline_id: Optional[str] = None
    sync_status: Optional[str] = "synced"
