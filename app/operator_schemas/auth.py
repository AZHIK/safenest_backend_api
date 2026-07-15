"""
Operator Authentication Schemas

Separate authentication system for institutional operators.
Do NOT mix with survivor mobile app auth.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator
from app.utils.validators import clean_tanzania_phone


class OperatorLoginRequest(BaseModel):
    """Operator login request."""
    email: EmailStr = Field(..., description="Operator email address")
    password: str = Field(..., min_length=8, description="Operator password")


class OperatorRegisterRequest(BaseModel):
    """Operator self-registration request."""
    full_name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr = Field(..., description="Operator email address")
    password: str = Field(..., min_length=12, description="Operator password")
    phone: Optional[str] = Field(None, max_length=20)
    organization: Optional[str] = Field(None, max_length=100)
    role: Optional[str] = Field(None, description="Role name to assign (e.g. police, help_center)")

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        if v:
            return clean_tanzania_phone(v)
        return v


class OperatorTokenResponse(BaseModel):
    """Operator JWT token response."""
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Access token expiry in seconds")
    refresh_expires_in: int = Field(..., description="Refresh token expiry in seconds")
    setup_completed: bool = Field(default=False, description="Whether the operator has completed setup")


class OperatorTokenRefreshRequest(BaseModel):
    """Token refresh request."""
    refresh_token: str = Field(..., description="Valid refresh token")


class OperatorMeResponse(BaseModel):
    """Current operator profile response."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    full_name: str
    email: str
    phone: Optional[str]
    is_active: bool
    is_super_admin: bool
    email_verified: bool
    last_login: Optional[datetime]
    created_at: datetime
    setup_completed: bool

    # Computed fields
    roles: list[str] = Field(default_factory=list, description="Assigned role names")


class OperatorPasswordChangeRequest(BaseModel):
    """Password change request."""
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=12, description="New password (min 12 chars)")
    confirm_password: str = Field(..., description="Confirm new password")


class OperatorPasswordResetRequest(BaseModel):
    """Password reset request."""
    email: EmailStr = Field(..., description="Operator email for password reset")


class OperatorPasswordResetConfirmRequest(BaseModel):
    """Password reset confirmation."""
    token: str = Field(..., description="Password reset token")
    new_password: str = Field(..., min_length=12, description="New password (min 12 chars)")
    confirm_password: str = Field(..., description="Confirm new password")
