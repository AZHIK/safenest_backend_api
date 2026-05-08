import uuid
from datetime import datetime
from enum import Enum
from typing import List, Optional, TYPE_CHECKING

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, JSON, String, Text, func
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .user import User

class SOSStatus(str, Enum):
    ACTIVE = "active"
    RESOLVED = "resolved"
    CANCELLED = "cancelled"
    ESCALATED = "escalated"
    ASSIGNED = "assigned"


class SOSAlert(SQLModel, table=True):
    __tablename__ = "sos_alerts"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: Optional[uuid.UUID] = Field(default=None, sa_column=Column(ForeignKey("users.id", ondelete="SET NULL"), index=True))

    # Status tracking
    status: str = Field(default=SOSStatus.ACTIVE, max_length=20, index=True)
    alert_type: str = Field(default="manual", max_length=30)  # manual, timer, gesture, voice
    severity: str = Field(default="high", max_length=20)  # low, medium, high, critical

    # Initial location
    initial_latitude: float = Field(...)
    initial_longitude: float = Field(...)
    initial_accuracy: Optional[float] = Field(default=None)
    initial_address: Optional[str] = Field(default=None, sa_column=Column(Text))

    # Context
    message: Optional[str] = Field(default=None, sa_column=Column(Text))  # Optional message from user
    triggered_by_device_id: Optional[str] = Field(default=None, max_length=64)
    battery_level: Optional[int] = Field(default=None)

    # Notification tracking
    contacts_notified: int = Field(default=0)
    centers_notified: list = Field(default_factory=list, sa_column=Column(JSON))  # List of support center IDs notified

    # Assignment & Resolution (Institutional Operators)
    assigned_to: Optional[uuid.UUID] = Field(default=None, sa_column=Column(ForeignKey("operator_users.id", ondelete="SET NULL")))
    assigned_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True)))
    resolved_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True)))
    resolved_by: Optional[uuid.UUID] = Field(default=None, sa_column=Column(ForeignKey("operator_users.id", ondelete="SET NULL")))
    resolution_notes: Optional[str] = Field(default=None, sa_column=Column(Text))

    created_at: datetime = Field(default=None, sa_column=Column(DateTime(timezone=True), server_default=func.now(), index=True))
    updated_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True), onupdate=func.now()))

    # Sync fields for offline support
    client_created_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True)))
    sync_status: str = Field(default="synced", max_length=20)  # synced, pending, conflict
    offline_id: Optional[str] = Field(default=None, max_length=64, index=True)  # ID generated on client when offline

    # Relationships
    user: Optional["User"] = Relationship(
        back_populates="sos_alerts",
        sa_relationship_kwargs={"foreign_keys": "SOSAlert.user_id"}
    )
    location_pings: List["LocationPing"] = Relationship(
        back_populates="alert",
        sa_relationship_kwargs={"cascade": "all, delete-orphan", "foreign_keys": "LocationPing.alert_id"}
    )

    def __repr__(self):
        return f"<SOSAlert(id={self.id}, status={self.status}, user_id={self.user_id})>"


class LocationPing(SQLModel, table=True):
    __tablename__ = "location_pings"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    alert_id: uuid.UUID = Field(sa_column=Column(ForeignKey("sos_alerts.id", ondelete="CASCADE"), index=True))
    user_id: Optional[uuid.UUID] = Field(default=None, sa_column=Column(ForeignKey("users.id", ondelete="SET NULL"), index=True))

    latitude: float = Field(...)
    longitude: float = Field(...)
    accuracy: Optional[float] = Field(default=None)
    altitude: Optional[float] = Field(default=None)
    speed: Optional[float] = Field(default=None)
    heading: Optional[float] = Field(default=None)

    # Device context
    battery_level: Optional[int] = Field(default=None)
    network_type: Optional[str] = Field(default=None, max_length=20)  # wifi, cellular, offline
    signal_strength: Optional[int] = Field(default=None)

    # Timestamp - crucial for tracking
    recorded_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False, index=True))
    received_at: datetime = Field(default=None, sa_column=Column(DateTime(timezone=True), server_default=func.now()))

    # Sync fields
    offline_sequence: Optional[int] = Field(default=None)  # For ordering offline-synced pings

    # Relationships
    alert: "SOSAlert" = Relationship(
        back_populates="location_pings",
        sa_relationship_kwargs={"foreign_keys": "LocationPing.alert_id"}
    )

    def __repr__(self):
        return f"<LocationPing(id={self.id}, alert_id={self.alert_id}, lat={self.latitude}, lng={self.longitude})>"
