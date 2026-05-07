"""
Operator User Management Schemas
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class OperatorUserCreate(BaseModel):
    """Create a new operator user."""
    full_name: str = Field(..., min_length=2, max_length=200)
    email: EmailStr
    phone: Optional[str] = Field(default=None, max_length=30)
    password: str = Field(..., min_length=12, description="Initial password (min 12 chars)")
    is_active: bool = Field(default=True)
    is_super_admin: bool = Field(default=False)
    role_ids: List[UUID] = Field(default_factory=list, description="Initial role assignments")


class OperatorUserUpdate(BaseModel):
    """Update operator user."""
    full_name: Optional[str] = Field(default=None, min_length=2, max_length=200)
    phone: Optional[str] = Field(default=None, max_length=30)
    is_active: Optional[bool] = None
    # Note: is_super_admin changes should be done via dedicated endpoint for audit


class OperatorUserStatusUpdate(BaseModel):
    """Update operator user status."""
    is_active: bool
    reason: Optional[str] = Field(default=None, description="Reason for status change")


class OperatorUserRead(BaseModel):
    """Operator user response schema."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    full_name: str
    email: str
    phone: Optional[str]
    is_active: bool
    is_super_admin: bool
    email_verified: bool
    last_login: Optional[datetime]
    locked_until: Optional[datetime]
    created_at: datetime
    updated_at: Optional[datetime]

    # Computed
    roles: List[str] = Field(default_factory=list, description="Assigned role names")
    role_count: int = Field(default=0)
    direct_permission_count: int = Field(default=0)


class OperatorUserDetailRead(OperatorUserRead):
    """Operator user with full details."""
    role_details: List[dict] = Field(default_factory=list, description="Role objects")
    direct_permissions: List["PermissionOverrideItem"] = Field(default_factory=list)


class PermissionOverrideItem(BaseModel):
    """Direct permission override item."""
    permission_code: str
    granted: bool  # True=grant, False=deny
    reason: Optional[str]
    created_at: datetime
    created_by: Optional[UUID]


class AssignRolesToUserRequest(BaseModel):
    """Assign roles to a user."""
    role_ids: List[UUID] = Field(..., min_length=1, description="Role IDs to assign")
    replace_existing: bool = Field(
        default=False,
        description="If true, replace all roles; if false, add to existing"
    )


class RemoveRolesFromUserRequest(BaseModel):
    """Remove roles from a user."""
    role_ids: List[UUID] = Field(..., min_length=1, description="Role IDs to remove")


class AssignDirectPermissionsRequest(BaseModel):
    """Assign direct permission overrides to a user."""
    permissions: List["DirectPermissionAssignment"] = Field(..., min_length=1)
    replace_existing: bool = Field(default=False)


class DirectPermissionAssignment(BaseModel):
    """Single permission assignment."""
    permission_code: str
    granted: bool = Field(default=True, description="True to grant, False to deny")
    reason: Optional[str] = Field(default=None, max_length=500)


class RemoveDirectPermissionsRequest(BaseModel):
    """Remove direct permission overrides."""
    permission_codes: List[str] = Field(..., min_length=1)


class OperatorUserListResponse(BaseModel):
    """Paginated operator user list response."""
    items: List[OperatorUserRead]
    total: int
    page: int
    page_size: int
    pages: int


class BulkOperatorActionRequest(BaseModel):
    """Bulk action on multiple operators."""
    user_ids: List[UUID] = Field(..., min_length=1, max_length=100)
    action: str = Field(..., pattern="^(activate|deactivate|delete)$")
    reason: Optional[str] = None
