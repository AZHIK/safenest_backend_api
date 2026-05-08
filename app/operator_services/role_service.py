"""
Role Management Service

Business logic for role CRUD and permission assignment.
"""

from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.operator_models.operator import Role
from app.operator_repositories.role import role_repo
from app.operator_schemas.role import RoleCreate, RoleUpdate
from app.rbac.permission_enum import PermissionEnum, SYSTEM_ROLE_PERMISSIONS
from app.rbac.services.permission_resolver_service import permission_resolver

logger = get_logger(__name__)


class RoleService:
    """Role management business logic."""

    def __init__(self):
        self._role_repo = role_repo

    async def create_role(
        self,
        db: AsyncSession,
        data: RoleCreate,
        created_by: Optional[UUID] = None
    ) -> Tuple[Optional[Role], str]:
        """Create a new role.
        
        Returns: (role, message)
        """
        # Check if name exists
        if await role_repo.name_exists(db, data.name):
            return None, "Role with this name already exists"
        
        # Validate permission codes
        invalid_perms = self._validate_permissions(data.permission_codes)
        if invalid_perms:
            return None, f"Invalid permission codes: {', '.join(invalid_perms)}"
        
        # Create role
        role = Role(
            name=data.name,
            description=data.description,
            is_system=False  # User-created roles are never system roles
        )
        db.add(role)
        await db.flush()
        
        # Assign permissions if provided
        if data.permission_codes:
            await role_repo.assign_permissions(
                db,
                role.id,
                data.permission_codes,
                replace_existing=True
            )
        
        await db.commit()
        
        logger.info(
            "role_created",
            role_id=str(role.id),
            name=data.name,
            permission_count=len(data.permission_codes),
            created_by=str(created_by) if created_by else None
        )
        
        return role, "Role created successfully"

    async def update_role(
        self,
        db: AsyncSession,
        role_id: UUID,
        data: RoleUpdate,
        updated_by: Optional[UUID] = None
    ) -> Tuple[Optional[Role], str]:
        """Update an existing role."""
        role = await role_repo.get_by_id(db, role_id)
        if not role:
            return None, "Role not found"
        
        # Cannot modify system roles' names
        if role.is_system and data.name and data.name != role.name:
            return None, "Cannot modify system role name"
        
        # Check name uniqueness if changing
        if data.name and data.name != role.name:
            if await role_repo.name_exists(db, data.name, exclude_role_id=role_id):
                return None, "Role name already in use"
            role.name = data.name
        
        if data.description is not None:
            role.description = data.description
        
        await db.flush()
        
        logger.info(
            "role_updated",
            role_id=str(role_id),
            updated_by=str(updated_by) if updated_by else None
        )
        
        return role, "Role updated successfully"

    async def delete_role(
        self,
        db: AsyncSession,
        role_id: UUID,
        deleted_by: Optional[UUID] = None
    ) -> Tuple[bool, str]:
        """Delete a role."""
        role = await role_repo.get_by_id(db, role_id)
        if not role:
            return False, "Role not found"
        
        # Cannot delete system roles
        if role.is_system:
            return False, "Cannot delete system roles"
        
        # Check if role has users
        user_count = await role_repo.get_role_user_count(db, role_id)
        if user_count > 0:
            return False, f"Cannot delete role with {user_count} assigned users"
        
        await role_repo.delete(db, role_id)
        
        logger.info(
            "role_deleted",
            role_id=str(role_id),
            deleted_by=str(deleted_by) if deleted_by else None
        )
        
        return True, "Role deleted successfully"

    async def assign_permissions_to_role(
        self,
        db: AsyncSession,
        role_id: UUID,
        permission_codes: List[str],
        replace_existing: bool = False,
        assigned_by: Optional[UUID] = None
    ) -> Tuple[bool, str]:
        """Assign permissions to a role."""
        role = await role_repo.get_by_id(db, role_id)
        if not role:
            return False, "Role not found"
        
        # Validate permission codes
        invalid_perms = self._validate_permissions(permission_codes)
        if invalid_perms:
            return False, f"Invalid permission codes: {', '.join(invalid_perms)}"
        
        # Assign permissions
        await role_repo.assign_permissions(
            db,
            role_id,
            permission_codes,
            replace_existing
        )
        
        await db.commit()
        
        # Invalidate cache for all users with this role
        await permission_resolver.invalidate_cache_for_role(db, role_id)
        
        logger.info(
            "role_permissions_assigned",
            role_id=str(role_id),
            permission_count=len(permission_codes),
            replace_existing=replace_existing,
            assigned_by=str(assigned_by) if assigned_by else None
        )
        
        return True, "Permissions assigned successfully"

    async def remove_permissions_from_role(
        self,
        db: AsyncSession,
        role_id: UUID,
        permission_codes: List[str],
        removed_by: Optional[UUID] = None
    ) -> Tuple[bool, str]:
        """Remove permissions from a role."""
        role = await role_repo.get_by_id(db, role_id)
        if not role:
            return False, "Role not found"
        
        count = await role_repo.remove_permissions(db, role_id, permission_codes)
        await db.commit()
        
        # Invalidate cache for all users with this role
        await permission_resolver.invalidate_cache_for_role(db, role_id)
        
        logger.info(
            "role_permissions_removed",
            role_id=str(role_id),
            removed_count=count,
            removed_by=str(removed_by) if removed_by else None
        )
        
        return True, f"Removed {count} permissions from role"

    async def get_role_with_permissions(
        self,
        db: AsyncSession,
        role_id: UUID
    ) -> Tuple[Optional[Role], List[str]]:
        """Get role with its permissions."""
        role = await role_repo.get_by_id_with_permissions(db, role_id)
        if not role:
            return None, []
        
        permissions = [p.permission_code for p in role.permission_links]
        return role, permissions

    async def list_roles(
        self,
        db: AsyncSession,
        is_system: Optional[bool] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 50
    ) -> Tuple[List[Role], int]:
        """List roles with pagination."""
        return await role_repo.list_roles(db, is_system, search, page, page_size)

    async def initialize_system_roles(self, db: AsyncSession) -> None:
        """Initialize predefined system roles on first run."""
        existing_roles = await role_repo.list_roles(db, is_system=True, page_size=100)
        existing_names = {r.name for r in existing_roles[0]}
        
        for role_name, permissions in SYSTEM_ROLE_PERMISSIONS.items():
            if role_name in existing_names:
                continue
            
            # Create system role
            role = Role(
                name=role_name,
                description=f"System role: {role_name}",
                is_system=True
            )
            db.add(role)
            await db.flush()
            
            # Assign permissions
            await role_repo.assign_permissions(
                db,
                role.id,
                list(permissions),
                replace_existing=True
            )
            
            logger.info("system_role_initialized", role_name=role_name, permission_count=len(permissions))
        
        await db.commit()

    def _validate_permissions(self, permission_codes: List[str]) -> List[str]:
        """Validate permission codes against PermissionEnum.
        
        Returns list of invalid permission codes.
        """
        valid_perms = PermissionEnum.all_permissions()
        return [p for p in permission_codes if p not in valid_perms]


# Global instance
role_service = RoleService()
