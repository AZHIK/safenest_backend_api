from __future__ import annotations
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class OTPRequest(BaseModel):
    phone_number: str = Field(..., min_length=10, max_length=20)
    country_code: str = Field(default="+1", pattern=r"^\+[1-9]\d{0,3}$")

    @field_validator("phone_number")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        digits = "".join(c for c in v if c.isdigit())
        if len(digits) < 8:
            raise ValueError("Phone number must have at least 8 digits")
        return digits


class OTPVerify(BaseModel):
    phone_number: str = Field(..., min_length=10, max_length=20)
    otp_code: str = Field(..., min_length=4, max_length=8, pattern=r"^\d+$")
    country_code: Optional[str] = Field(default=None)

    @field_validator("phone_number")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        digits = "".join(c for c in v if c.isdigit())
        if len(digits) < 8:
            raise ValueError("Phone number must have at least 8 digits")
        return digits


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: "UserResponse"


class AnonymousSessionCreate(BaseModel):
    device_fingerprint: Optional[str] = Field(default=None, max_length=64)
    language_preference: str = Field(default="en", max_length=10)


class AnonymousSessionResponse(BaseModel):
    session_token: str
    user: "UserResponse"
    expires_at: datetime


class TrustedContactBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    phone_number: str = Field(..., min_length=8, max_length=20)
    relationship: Optional[str] = Field(default=None, max_length=50)
    priority: int = Field(default=1, ge=1, le=5)
    notify_sms: bool = True
    notify_push: bool = True


class TrustedContactCreate(TrustedContactBase):
    pass


class TrustedContactResponse(TrustedContactBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    is_verified: bool
    created_at: datetime


class UserBase(BaseModel):
    phone_number: Optional[str] = None
    country_code: Optional[str] = None
    is_anonymous: bool = False
    is_verified: bool = False
    language_preference: str = "en"


class UserCreate(UserBase):
    pass


class UserUpdate(BaseModel):
    nickname: Optional[str] = Field(default=None, max_length=50)
    language_preference: Optional[str] = Field(default=None, max_length=10)
    emergency_message_template: Optional[str] = Field(default=None, max_length=500)


class UserResponse(UserBase):
    id: UUID
    status: str
    last_login_at: Optional[datetime] = None
    created_at: datetime
    trusted_contacts: Optional[list[TrustedContactResponse]] = None


# Mapper functions for safe ORM -> Schema conversion
# These must be called ONLY after all relationships are eagerly loaded

def to_trusted_contact_response(contact) -> TrustedContactResponse:
    """Convert TrustedContact ORM to response schema."""
    return TrustedContactResponse(
        id=contact.id,
        name=contact.name,
        phone_number=contact.phone_number,
        relationship=contact.relationship,
        priority=contact.priority,
        notify_sms=contact.notify_sms,
        notify_push=contact.notify_push,
        is_verified=contact.is_verified,
        created_at=contact.created_at
    )


def to_user_response(user) -> UserResponse:
    """Convert User ORM to response schema. Must be called after trusted_contacts is eager-loaded."""
    return UserResponse(
        id=user.id,
        phone_number=user.phone_number,
        country_code=user.country_code,
        is_anonymous=user.is_anonymous,
        is_verified=user.is_verified,
        language_preference=user.language_preference,
        status=user.status,
        last_login_at=user.last_login_at,
        created_at=user.created_at,
        trusted_contacts=[
            to_trusted_contact_response(tc)
            for tc in (user.trusted_contacts or [])
        ] if user.trusted_contacts else []
    )


def to_token_response(access_token: str, refresh_token: str, expires_in: int, user) -> TokenResponse:
    """Create TokenResponse from tokens and User ORM."""
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_in,
        user=to_user_response(user)
    )


def to_anonymous_session_response(session_token: str, user, expires_at: datetime) -> AnonymousSessionResponse:
    """Create AnonymousSessionResponse from token and User ORM."""
    return AnonymousSessionResponse(
        session_token=session_token,
        user=to_user_response(user),
        expires_at=expires_at
    )
