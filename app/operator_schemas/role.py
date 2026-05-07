"""
Role Management Schemas
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class RoleCreate(BaseModel):
    """Create a new role."""
    name: str = Field(..., min_length=2, max_length=100, description="Unique role name")
    description: Optional[str] = Field(default=None, max_length=500, description="Role description")
    permission_codes: List[str] = Field(
        default_factory=list,
        description="List of PermissionEnum values to assign"
    )


class RoleUpdate(BaseModel):
    """Update existing role."""
    name: Optional[str] = Field(default=None, min_length=2, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)


class RolePermissionItem(BaseModel):
    """Permission assigned to role."""
    permission_code: str
    assigned_at: datetime


class RoleRead(BaseModel):
    """Role response schema."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: Optional[str]
    is_system: bool
    created_at: datetime
    updated_at: Optional[datetime]

    # Computed
    permission_count: int = Field(default=0, description="Number of assigned permissions")
    user_count: int = Field(default=0, description="Number of users with this role")


class RoleDetailRead(RoleRead):
    """Role with full permissions list."""
    permissions: List[str] = Field(default_factory=list, description="Assigned permission codes")


class AssignPermissionsToRoleRequest(BaseModel):
    """Assign permissions to a role."""
    permission_codes: List[str] = Field(
        ...,
        min_length=1,
        description="List of PermissionEnum values"
    )
    replace_existing: bool = Field(
        default=False,
        description="If true, replace all existing permissions; if false, add to existing"
    )


class RemovePermissionsFromRoleRequest(BaseModel):
    """Remove permissions from a role."""
    permission_codes: List[str] = Field(..., min_length=1, description="Permissions to remove")


class RoleListResponse(BaseModel):
    """Paginated role list response."""
    items: List[RoleRead]
    total: int
    page: int
    page_size: int
    pages: int


class RoleUserAssignment(BaseModel):
    """User assigned to role."""
    user_id: UUID
    user_email: str
    user_name: str
    assigned_at: datetime
