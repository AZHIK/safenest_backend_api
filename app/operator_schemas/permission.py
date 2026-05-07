"""
Permission and Menu Schemas
"""

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class PermissionItem(BaseModel):
    """Single permission item."""
    code: str
    description: str
    module: str


class PermissionGroupResponse(BaseModel):
    """Grouped permissions response."""
    module: str
    permissions: List[PermissionItem]


class PermissionsRegistryResponse(BaseModel):
    """All available permissions grouped by module."""
    groups: List[PermissionGroupResponse]
    total_count: int


class EffectivePermissionsResponse(BaseModel):
    """Current operator's effective permissions."""
    permissions: List[str] = Field(description="List of effective permission codes")
    is_super_admin: bool
    role_derived: List[str] = Field(description="Permissions from roles")
    direct_grants: List[str] = Field(description="Directly granted permissions")
    direct_denies: List[str] = Field(description="Directly denied permissions (overrides)")


class MenuItem(BaseModel):
    """Sidebar menu item."""
    id: str
    label: str
    icon: Optional[str] = None
    route: Optional[str] = None
    children: Optional[List["MenuItem"]] = None
    required_permission: Optional[str] = None
    required_permissions: Optional[List[str]] = None  # Any of these
    badge: Optional[str] = None
    badge_color: Optional[str] = None


class SidebarMenuResponse(BaseModel):
    """Sidebar menu based on operator permissions."""
    items: List[MenuItem]
    user_info: Dict[str, str] = Field(description="Current user info for display")


class PermissionCheckRequest(BaseModel):
    """Check if operator has specific permissions."""
    permissions: List[str] = Field(..., min_length=1)
    require_all: bool = Field(default=True, description="True=ALL required, False=ANY required")


class PermissionCheckResponse(BaseModel):
    """Permission check result."""
    has_permission: bool
    checked_permissions: List[str]
    missing_permissions: List[str]
