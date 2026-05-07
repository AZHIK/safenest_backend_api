"""
Operator User Management API Routes

- GET /api/v1/operator/users - List operator users
- POST /api/v1/operator/users - Create operator user
- POST /api/v1/operator/users/{id}/assign-roles - Assign roles to user
- POST /api/v1/operator/users/{id}/assign-direct-permissions - Assign direct permissions
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.operator_auth import (
    get_current_operator,
    require_operator_permission,
    require_all_operator_permissions,
    require_operator_super_admin,
)
from app.operator_models.operator import OperatorUser, UserRoleLink
from app.operator_schemas.operator_user import (
    OperatorUserCreate,
    OperatorUserRead,
    OperatorUserDetailRead,
    OperatorUserUpdate,
    AssignRolesToUserRequest,
    AssignDirectPermissionsRequest,
    PermissionOverrideItem,
    OperatorUserListResponse,
    OperatorUserStatusUpdate,
)
from app.operator_services.operator_user_service import operator_user_service
from app.rbac.services.permission_resolver_service import permission_resolver
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


def to_user_read(user: OperatorUser) -> OperatorUserRead:
    """Convert OperatorUser model to OperatorUserRead schema."""
    role_names = [
        link.role.name for link in user.role_links
        if link.role
    ] if user.role_links else []
    
    return OperatorUserRead(
        id=user.id,
        full_name=user.full_name,
        email=user.email,
        phone=user.phone,
        is_active=user.is_active,
        is_super_admin=user.is_super_admin,
        email_verified=user.email_verified,
        last_login=user.last_login,
        locked_until=user.locked_until,
        created_at=user.created_at,
        updated_at=user.updated_at,
        roles=role_names,
        role_count=len(role_names),
        direct_permission_count=len(user.permission_overrides) if user.permission_overrides else 0
    )


@router.get(
    "",
    response_model=OperatorUserListResponse,
    dependencies=[Depends(require_operator_permission("operators.view"))]
)
async def list_users(
    is_active: Optional[bool] = Query(default=None),
    is_super_admin: Optional[bool] = Query(default=None),
    role_id: Optional[UUID] = Query(default=None),
    search: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """List operator users with filtering and pagination."""
    users, total = await operator_user_service.list_users(
        db, is_active, is_super_admin, role_id, search, page, page_size
    )
    
    return OperatorUserListResponse(
        items=[to_user_read(u) for u in users],
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size
    )


@router.post(
    "",
    response_model=OperatorUserRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_operator_permission("operators.create"))]
)
async def create_user(
    data: OperatorUserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: OperatorUser = Depends(get_current_operator)
):
    """Create a new operator user."""
    # Only super admins can create super admins
    if data.is_super_admin and not current_user.is_super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only super admins can create super admin accounts"
        )
    
    user, message = await operator_user_service.create_user(
        db, data, created_by=current_user.id
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )
    
    # Load roles for response
    user = await operator_user_service.get_user_with_roles(db, user.id)
    return to_user_read(user)


@router.get(
    "/{user_id}",
    response_model=OperatorUserDetailRead,
    dependencies=[Depends(require_operator_permission("operators.view"))]
)
async def get_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get operator user details."""
    user = await operator_user_service.get_user_with_permissions(db, user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Build role details
    role_details = []
    if user.role_links:
        for link in user.role_links:
            if link.role:
                role_details.append({
                    "id": str(link.role.id),
                    "name": link.role.name,
                    "is_system": link.role.is_system
                })
    
    # Build permission overrides
    direct_perms: List[PermissionOverrideItem] = []
    if user.permission_overrides:
        for override in user.permission_overrides:
            direct_perms.append(PermissionOverrideItem(
                permission_code=override.permission_code,
                granted=override.granted,
                reason=override.reason,
                created_at=override.created_at,
                created_by=override.created_by
            ))
    
    basic = to_user_read(user)
    return OperatorUserDetailRead(
        **basic.model_dump(),
        role_details=role_details,
        direct_permissions=direct_perms
    )


@router.put(
    "/{user_id}",
    response_model=OperatorUserRead,
    dependencies=[Depends(require_operator_permission("operators.update"))]
)
async def update_user(
    user_id: UUID,
    data: OperatorUserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: OperatorUser = Depends(get_current_operator)
):
    """Update operator user."""
    # Users can only update themselves or users with fewer privileges
    target_user = await operator_user_service.get_user_with_roles(db, user_id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Prevent non-super-admins from modifying super admins
    if target_user.is_super_admin and not current_user.is_super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot modify super admin users"
        )
    
    user, message = await operator_user_service.update_user(
        db, user_id, data, updated_by=current_user.id
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )
    
    user = await operator_user_service.get_user_with_roles(db, user.id)
    return to_user_read(user)


@router.patch(
    "/{user_id}/status",
    response_model=OperatorUserRead,
    dependencies=[Depends(require_operator_permission("operators.suspend"))]
)
async def update_user_status(
    user_id: UUID,
    data: OperatorUserStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: OperatorUser = Depends(get_current_operator)
):
    """Activate or deactivate operator user."""
    target_user = await operator_user_service.get_user_with_roles(db, user_id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Prevent deactivating yourself
    if user_id == current_user.id and not data.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate your own account"
        )
    
    # Prevent deactivating super admins (only super admins can)
    if target_user.is_super_admin and not current_user.is_super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only super admins can deactivate super admin accounts"
        )
    
    from app.operator_schemas.operator_user import OperatorUserUpdate
    update_data = OperatorUserUpdate(is_active=data.is_active)
    
    user, message = await operator_user_service.update_user(
        db, user_id, update_data, updated_by=current_user.id
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )
    
    user = await operator_user_service.get_user_with_roles(db, user.id)
    return to_user_read(user)


@router.patch(
    "/{user_id}/super-admin",
    response_model=OperatorUserRead,
    dependencies=[Depends(require_operator_super_admin)]
)
async def update_super_admin_status(
    user_id: UUID,
    is_super_admin: bool = Query(..., description="Set super admin status"),
    db: AsyncSession = Depends(get_db),
    current_user: OperatorUser = Depends(get_current_operator)
):
    """Grant or revoke super admin status (super admin only)."""
    success, message = await operator_user_service.update_super_admin_status(
        db, user_id, is_super_admin, updated_by=current_user.id
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )
    
    user = await operator_user_service.get_user_with_roles(db, user_id)
    return to_user_read(user)


@router.post(
    "/{user_id}/assign-roles",
    dependencies=[Depends(require_all_operator_permissions(
        "operators.view", "operators.assign_roles"
    ))]
)
async def assign_roles_to_user(
    user_id: UUID,
    data: AssignRolesToUserRequest,
    db: AsyncSession = Depends(get_db),
    current_user: OperatorUser = Depends(get_current_operator)
):
    """Assign roles to an operator user."""
    success, message = await operator_user_service.assign_roles_to_user(
        db,
        user_id,
        data.role_ids,
        replace_existing=data.replace_existing,
        assigned_by=current_user.id
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )
    
    user = await operator_user_service.get_user_with_roles(db, user_id)
    return to_user_read(user)


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_operator_permission("operators.delete"))]
)
async def delete_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: OperatorUser = Depends(get_current_operator)
):
    """Delete an operator user."""
    success, message = await operator_user_service.delete_user(
        db, user_id, deleted_by=current_user.id
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )


@router.post(
    "/{user_id}/assign-direct-permissions",
    response_model=OperatorUserDetailRead,
    dependencies=[Depends(require_all_operator_permissions(
        "operators.view", "operators.manage_permissions"
    ))]
)
async def assign_direct_permissions(
    user_id: UUID,
    data: AssignDirectPermissionsRequest,
    db: AsyncSession = Depends(get_db),
    current_user: OperatorUser = Depends(get_current_operator)
):
    """Assign direct permission overrides to a user."""
    success, message = await operator_user_service.assign_direct_permissions(
        db,
        user_id,
        data.permissions,
        replace_existing=data.replace_existing,
        assigned_by=current_user.id
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )
    
    # Return updated user with permissions
    user = await operator_user_service.get_user_with_permissions(db, user_id)
    role_details = [
        {"id": str(link.role.id), "name": link.role.name, "is_system": link.role.is_system}
        for link in user.role_links if link.role
    ] if user.role_links else []
    
    direct_perms = [
        PermissionOverrideItem(
            permission_code=o.permission_code,
            granted=o.granted,
            reason=o.reason,
            created_at=o.created_at,
            created_by=o.created_by
        )
        for o in user.permission_overrides
    ] if user.permission_overrides else []
    
    basic = to_user_read(user)
    return OperatorUserDetailRead(
        **basic.model_dump(),
        role_details=role_details,
        direct_permissions=direct_perms
    )
