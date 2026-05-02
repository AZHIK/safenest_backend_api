from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import LocationBase, OfflineSyncMixin


class SOSCreate(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    accuracy: Optional[float] = Field(default=None, ge=0)
    altitude: Optional[float] = None
    speed: Optional[float] = None
    heading: Optional[float] = None
    battery_level: Optional[int] = Field(default=None, ge=0, le=100)
    network_type: Optional[str] = None
    alert_type: str = Field(default="manual")  # manual, timer, gesture, voice
    message: Optional[str] = Field(default=None, max_length=500)
    triggered_by_device_id: Optional[str] = Field(default=None, max_length=64)

    # Offline support
    client_created_at: Optional[datetime] = None
    offline_id: Optional[str] = Field(default=None, max_length=64)


class SOSStatusUpdate(BaseModel):
    status: str  # resolved, cancelled
    resolution_notes: Optional[str] = Field(default=None, max_length=1000)


class SOSResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    status: str
    alert_type: str
    severity: str
    initial_latitude: float
    initial_longitude: float
    initial_accuracy: Optional[float]
    initial_address: Optional[str]
    message: Optional[str]
    contacts_notified: int
    created_at: datetime
    updated_at: Optional[datetime]
    client_created_at: Optional[datetime]
    offline_id: Optional[str]


class LocationPingCreate(BaseModel):
    alert_id: UUID
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    accuracy: Optional[float] = Field(default=None, ge=0)
    altitude: Optional[float] = None
    speed: Optional[float] = None
    heading: Optional[float] = None
    battery_level: Optional[int] = Field(default=None, ge=0, le=100)
    network_type: Optional[str] = None
    signal_strength: Optional[int] = None
    recorded_at: datetime
    offline_sequence: Optional[int] = None


class LocationPingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    alert_id: UUID
    latitude: float
    longitude: float
    accuracy: Optional[float]
    recorded_at: datetime
    received_at: datetime


class SOSWithLocationsResponse(SOSResponse):
    recent_locations: list[LocationPingResponse] = []


# Mapper functions for safe ORM -> Schema conversion
# These must be called ONLY after all relationships are eagerly loaded

def to_location_ping_response(ping) -> LocationPingResponse:
    """Convert LocationPing ORM to response schema."""
    return LocationPingResponse(
        id=ping.id,
        alert_id=ping.alert_id,
        latitude=ping.latitude,
        longitude=ping.longitude,
        accuracy=ping.accuracy,
        recorded_at=ping.recorded_at,
        received_at=ping.received_at
    )


def to_sos_response(alert) -> SOSResponse:
    """Convert SOSAlert ORM to response schema."""
    return SOSResponse(
        id=alert.id,
        user_id=alert.user_id,
        status=alert.status,
        alert_type=alert.alert_type,
        severity=alert.severity,
        initial_latitude=alert.initial_latitude,
        initial_longitude=alert.initial_longitude,
        initial_accuracy=alert.initial_accuracy,
        initial_address=alert.initial_address,
        message=alert.message,
        contacts_notified=alert.contacts_notified,
        created_at=alert.created_at,
        updated_at=alert.updated_at,
        client_created_at=alert.client_created_at,
        offline_id=alert.offline_id
    )


def to_sos_with_locations_response(alert) -> SOSWithLocationsResponse:
    """Convert SOSAlert ORM with location_pings to response schema."""
    return SOSWithLocationsResponse(
        id=alert.id,
        user_id=alert.user_id,
        status=alert.status,
        alert_type=alert.alert_type,
        severity=alert.severity,
        initial_latitude=alert.initial_latitude,
        initial_longitude=alert.initial_longitude,
        initial_accuracy=alert.initial_accuracy,
        initial_address=alert.initial_address,
        message=alert.message,
        contacts_notified=alert.contacts_notified,
        created_at=alert.created_at,
        updated_at=alert.updated_at,
        client_created_at=alert.client_created_at,
        offline_id=alert.offline_id,
        recent_locations=[
            to_location_ping_response(p)
            for p in (getattr(alert, 'location_pings', None) or [])
        ]
    )
