"""
Permission Registry API Routes

GET /api/v1/operator/permissions - List all available permissions
"""

from typing import List

from fastapi import APIRouter, Depends, status

from app.operator_auth import get_current_operator
from app.operator_models.operator import OperatorUser
from app.operator_schemas.permission import (
    PermissionItem,
    PermissionGroupResponse,
    PermissionsRegistryResponse,
)
from app.rbac.permission_enum import PermissionEnum

router = APIRouter()


@router.get(
    "",
    response_model=PermissionsRegistryResponse,
    status_code=status.HTTP_200_OK
)
async def list_permissions(
    current_user: OperatorUser = Depends(get_current_operator)
):
    """
    Get all available permissions grouped by module.
    
    This endpoint returns the complete permission registry defined in PermissionEnum.
    Used by admin UI to populate permission assignment dropdowns.
    """
    grouped = PermissionEnum.grouped_by_module()
    
    groups: List[PermissionGroupResponse] = []
    for module, perm_codes in sorted(grouped.items()):
        # Generate human-readable descriptions
        permissions: List[PermissionItem] = []
        for code in sorted(perm_codes):
            parts = code.split(".")
            action = parts[-1] if len(parts) > 1 else code
            
            # Generate description based on action
            descriptions = {
                "view": "View",
                "view_all": "View All",
                "create": "Create",
                "update": "Update",
                "update_status": "Update Status",
                "delete": "Delete",
                "assign": "Assign",
                "respond": "Respond",
                "escalate": "Escalate",
                "close": "Close",
                "resolve": "Resolve",
                "export": "Export",
                "download": "Download",
                "upload": "Upload",
                "verify": "Verify",
                "merge": "Merge",
                "suspend": "Suspend",
                "manage": "Manage",
                "enroll_users": "Enroll Users",
                "view_progress": "View Progress",
                "schedule": "Schedule",
            }
            
            module_name = module.replace("_", " ").title()
            action_desc = descriptions.get(action, action.replace("_", " ").title())
            
            permissions.append(PermissionItem(
                code=code,
                description=f"{action_desc} {module_name}",
                module=module
            ))
        
        groups.append(PermissionGroupResponse(
            module=module,
            permissions=permissions
        ))
    
    return PermissionsRegistryResponse(
        groups=groups,
        total_count=len(PermissionEnum)
    )
