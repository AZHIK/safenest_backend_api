"""
Pydantic schemas for Operator RBAC system.
"""

from app.operator_schemas.auth import (
    OperatorLoginRequest,
    OperatorTokenResponse,
    OperatorTokenRefreshRequest,
    OperatorMeResponse,
    OperatorPasswordChangeRequest,
    OperatorPasswordResetRequest,
)

from app.operator_schemas.role import (
    RoleCreate,
    RoleUpdate,
    RoleRead,
    AssignPermissionsToRoleRequest,
    RolePermissionItem,
    RoleListResponse,
)

from app.operator_schemas.operator_user import (
    OperatorUserCreate,
    OperatorUserRead,
    OperatorUserUpdate,
    AssignRolesToUserRequest,
    AssignDirectPermissionsRequest,
    PermissionOverrideItem,
    OperatorUserListResponse,
    OperatorUserStatusUpdate,
)

from app.operator_schemas.permission import (
    PermissionGroupResponse,
    PermissionItem,
    EffectivePermissionsResponse,
    SidebarMenuResponse,
    MenuItem,
)

__all__ = [
    # Auth schemas
    "OperatorLoginRequest",
    "OperatorTokenResponse",
    "OperatorTokenRefreshRequest",
    "OperatorMeResponse",
    "OperatorPasswordChangeRequest",
    "OperatorPasswordResetRequest",
    # Role schemas
    "RoleCreate",
    "RoleUpdate",
    "RoleRead",
    "AssignPermissionsToRoleRequest",
    "RolePermissionItem",
    "RoleListResponse",
    # User schemas
    "OperatorUserCreate",
    "OperatorUserRead",
    "OperatorUserUpdate",
    "AssignRolesToUserRequest",
    "AssignDirectPermissionsRequest",
    "PermissionOverrideItem",
    "OperatorUserListResponse",
    "OperatorUserStatusUpdate",
    # Permission schemas
    "PermissionGroupResponse",
    "PermissionItem",
    "EffectivePermissionsResponse",
    "SidebarMenuResponse",
    "MenuItem",
]
