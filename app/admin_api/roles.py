"""
Role Management API Routes

- GET /api/v1/operator/roles - List roles
- POST /api/v1/operator/roles - Create role
- PUT /api/v1/operator/roles/{id} - Update role
- POST /api/v1/operator/roles/{id}/assign-permissions - Assign permissions to role
"""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.operator_auth import (
    get_current_operator,
    require_operator_permission,
    require_all_operator_permissions,
)
from app.operator_models.operator import OperatorUser
from app.operator_schemas.role import (
    RoleCreate,
    RoleRead,
    RoleDetailRead,
    RoleUpdate,
    AssignPermissionsToRoleRequest,
    RoleListResponse,
)
from app.operator_services.role_service import role_service

router = APIRouter()


def to_role_read(role, user_count: int = 0, permission_count: int = 0) -> RoleRead:
    """Convert Role model to RoleRead schema."""
    return RoleRead(
        id=role.id,
        name=role.name,
        description=role.description,
        is_system=role.is_system,
        created_at=role.created_at,
        updated_at=role.updated_at,
        user_count=user_count,
        permission_count=permission_count
    )


@router.get(
    "",
    response_model=RoleListResponse,
    dependencies=[Depends(require_operator_permission("roles.view"))]
)
async def list_roles(
    is_system: bool = Query(default=None, description="Filter by system role status"),
    search: str = Query(default=None, description="Search by name/description"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """List all roles with pagination and filtering."""
    roles, total = await role_service.list_roles(db, is_system, search, page, page_size)
    
    # Get counts for each role
    items: List[RoleRead] = []
    for role in roles:
        user_count = await role_service._role_repo.get_role_user_count(db, role.id)
        perm_count = await role_service._role_repo.get_role_permission_count(db, role.id)
        items.append(to_role_read(role, user_count, perm_count))
    
    return RoleListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size
    )


@router.post(
    "",
    response_model=RoleRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_operator_permission("roles.create"))]
)
async def create_role(
    data: RoleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: OperatorUser = Depends(get_current_operator)
):
    """Create a new role."""
    role, message = await role_service.create_role(
        db, data, created_by=current_user.id
    )
    
    if not role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )
    
    # Get counts
    user_count = await role_service._role_repo.get_role_user_count(db, role.id)
    perm_count = len(data.permission_codes)
    
    return to_role_read(role, user_count, perm_count)


@router.get(
    "/{role_id}",
    response_model=RoleDetailRead,
    dependencies=[Depends(require_operator_permission("roles.view"))]
)
async def get_role(
    role_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get role details including assigned permissions."""
    role, permissions = await role_service.get_role_with_permissions(db, role_id)
    
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )
    
    user_count = await role_service._role_repo.get_role_user_count(db, role_id)
    
    return RoleDetailRead(
        id=role.id,
        name=role.name,
        description=role.description,
        is_system=role.is_system,
        created_at=role.created_at,
        updated_at=role.updated_at,
        user_count=user_count,
        permission_count=len(permissions),
        permissions=permissions
    )


@router.put(
    "/{role_id}",
    response_model=RoleRead,
    dependencies=[Depends(require_operator_permission("roles.update"))]
)
async def update_role(
    role_id: UUID,
    data: RoleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: OperatorUser = Depends(get_current_operator)
):
    """Update an existing role."""
    role, message = await role_service.update_role(
        db, role_id, data, updated_by=current_user.id
    )
    
    if not role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )
    
    # Get counts
    user_count = await role_service._role_repo.get_role_user_count(db, role.id)
    perm_count = await role_service._role_repo.get_role_permission_count(db, role.id)
    
    return to_role_read(role, user_count, perm_count)


@router.delete(
    "/{role_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_operator_permission("roles.delete"))]
)
async def delete_role(
    role_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: OperatorUser = Depends(get_current_operator)
):
    """Delete a role (cannot delete system roles)."""
    success, message = await role_service.delete_role(
        db, role_id, deleted_by=current_user.id
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )


@router.post(
    "/{role_id}/assign-permissions",
    response_model=RoleDetailRead,
    dependencies=[Depends(require_all_operator_permissions(
        "roles.view", "roles.assign_permissions"
    ))]
)
async def assign_permissions_to_role(
    role_id: UUID,
    data: AssignPermissionsToRoleRequest,
    db: AsyncSession = Depends(get_db),
    current_user: OperatorUser = Depends(get_current_operator)
):
    """Assign permissions to a role."""
    success, message = await role_service.assign_permissions_to_role(
        db,
        role_id,
        data.permission_codes,
        replace_existing=data.replace_existing,
        assigned_by=current_user.id
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )
    
    # Return updated role
    role, permissions = await role_service.get_role_with_permissions(db, role_id)
    user_count = await role_service._role_repo.get_role_user_count(db, role_id)
    
    return RoleDetailRead(
        id=role.id,
        name=role.name,
        description=role.description,
        is_system=role.is_system,
        created_at=role.created_at,
        updated_at=role.updated_at,
        user_count=user_count,
        permission_count=len(permissions),
        permissions=permissions
    )
