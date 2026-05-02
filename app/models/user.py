import uuid
from datetime import datetime
from enum import Enum
from typing import List, Optional

from sqlalchemy import Column, DateTime, ForeignKey, String, Text, func
from sqlmodel import Field, Relationship, SQLModel
from typing import Optional, List, TYPE_CHECKING

from .sos import SOSAlert

if TYPE_CHECKING:
    from .sos import SOSAlert
    from .reporting import IncidentReport
    from .messaging import Message,ConversationParticipant


class UserStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    ANONYMOUS = "anonymous"


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    phone_number: Optional[str] = Field(default=None, max_length=20, unique=True, index=True)
    country_code: Optional[str] = Field(default=None, max_length=5)
    is_anonymous: bool = Field(default=False, index=True)
    is_verified: bool = Field(default=False)
    status: str = Field(default=UserStatus.ACTIVE, max_length=20, index=True)

    # Profile (minimal for privacy)
    nickname: Optional[str] = Field(default=None, max_length=50)
    language_preference: str = Field(default="en", max_length=10)
    emergency_message_template: Optional[str] = Field(default=None, sa_column=Column(Text))

    # Security
    last_login_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True)))
    created_at: datetime = Field(default=None, sa_column=Column(DateTime(timezone=True), server_default=func.now()))
    updated_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True), onupdate=func.now()))

    # Relationships
    trusted_contacts: List["TrustedContact"] = Relationship(back_populates="user", sa_relationship_kwargs={"cascade": "all, delete-orphan"})
    sos_alerts: List["SOSAlert"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"foreign_keys": "SOSAlert.user_id"}
    )
    incident_reports: List["IncidentReport"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"foreign_keys": "IncidentReport.user_id"}
    )
    sent_messages: List["Message"] = Relationship(
        back_populates="sender",
        sa_relationship_kwargs={"foreign_keys": "Message.sender_id"}
    )
    conversations: List["ConversationParticipant"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"foreign_keys": "ConversationParticipant.user_id"}
    )

    def __repr__(self):
        return f"<User(id={self.id}, phone={'***' if self.phone_number else 'None'}, anonymous={self.is_anonymous})>"


class AnonymousSession(SQLModel, table=True):
    __tablename__ = "anonymous_sessions"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    session_token: str = Field(max_length=128, unique=True, index=True)
    user_id: uuid.UUID = Field(sa_column=Column(ForeignKey("users.id", ondelete="CASCADE")))

    device_fingerprint: Optional[str] = Field(default=None, max_length=64, index=True)
    ip_address: Optional[str] = Field(default=None, max_length=45)  # IPv6 compatible
    expires_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    created_at: datetime = Field(default=None, sa_column=Column(DateTime(timezone=True), server_default=func.now()))

    # Sync tracking
    last_sync_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True)))
    sync_token: Optional[str] = Field(default=None, max_length=64)

    # Relationships
    user: "User" = Relationship(
        sa_relationship_kwargs={"foreign_keys": "AnonymousSession.user_id"}
    )

    def __repr__(self):
        return f"<AnonymousSession(id={self.id}, user_id={self.user_id})>"


class TrustedContact(SQLModel, table=True):
    __tablename__ = "trusted_contacts"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(sa_column=Column(ForeignKey("users.id", ondelete="CASCADE"), index=True))

    name: str = Field(max_length=100)
    phone_number: str = Field(max_length=20)
    relationship: Optional[str] = Field(default=None, max_length=50)
    priority: int = Field(default=1)  # 1 = highest priority

    notify_sms: bool = Field(default=True)
    notify_push: bool = Field(default=True)
    notify_call: bool = Field(default=False)

    is_verified: bool = Field(default=False)
    verification_code: Optional[str] = Field(default=None, max_length=10)

    created_at: datetime = Field(default=None, sa_column=Column(DateTime(timezone=True), server_default=func.now()))
    updated_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True), onupdate=func.now()))

    # Relationships
    user: "User" = Relationship(
        back_populates="trusted_contacts",
        sa_relationship_kwargs={"foreign_keys": "TrustedContact.user_id"}
    )

    def __repr__(self):
        return f"<TrustedContact(id={self.id}, name={self.name}, user_id={self.user_id})>"


class OTPCode(SQLModel, table=True):
    __tablename__ = "otp_codes"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    phone_number: str = Field(max_length=20, index=True)
    otp_hash: str = Field(max_length=128)  # Hashed OTP, not plain text
    purpose: str = Field(default="auth", max_length=20)  # auth, reset, verify_contact

    attempts: int = Field(default=0)
    max_attempts: int = Field(default=3)
    expires_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False, index=True))
    used_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True)))

    ip_address: Optional[str] = Field(default=None, max_length=45)
    user_agent_hash: Optional[str] = Field(default=None, max_length=64)

    created_at: datetime = Field(default=None, sa_column=Column(DateTime(timezone=True), server_default=func.now()))

    def __repr__(self):
        return f"<OTPCode(phone={'***'}, purpose={self.purpose}, expired={datetime.utcnow() > self.expires_at})>"
