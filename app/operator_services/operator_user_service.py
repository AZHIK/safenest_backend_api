"""
Operator User Management Service

Business logic for operator CRUD and role/permission assignment.
"""

from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy import delete, and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.operator_models.operator import OperatorUser, UserRoleLink
from app.operator_repositories.operator_user import operator_user_repo
from app.operator_repositories.role import role_repo
from app.operator_repositories.permission import permission_override_repo
from app.operator_schemas.operator_user import (
    OperatorUserCreate,
    OperatorUserUpdate,
    AssignRolesToUserRequest,
    AssignDirectPermissionsRequest,
    DirectPermissionAssignment,
)
from app.operator_services.operator_auth_service import operator_auth_service
from app.rbac.permission_enum import PermissionEnum
from app.rbac.services.permission_resolver_service import permission_resolver

logger = get_logger(__name__)


class OperatorUserService:
    """Operator user management business logic."""

    async def create_user(
        self,
        db: AsyncSession,
        data: OperatorUserCreate,
        created_by: Optional[UUID] = None
    ) -> Tuple[Optional[OperatorUser], str]:
        """Create a new operator user.
        
        Returns: (user, message)
        """
        # Check email uniqueness
        if await operator_user_repo.email_exists(db, data.email):
            return None, "Email already registered"
        
        # Validate role IDs if provided
        if data.role_ids:
            for role_id in data.role_ids:
                role = await role_repo.get_by_id(db, role_id)
                if not role:
                    return None, f"Role not found: {role_id}"
        
        # Create user
        user = operator_auth_service.create_user(
            full_name=data.full_name,
            email=data.email,
            password=data.password,
            phone=data.phone,
            is_super_admin=data.is_super_admin
        )
        db.add(user)
        await db.flush()
        
        # Assign roles if provided
        if data.role_ids:
            for role_id in data.role_ids:
                link = UserRoleLink(user_id=user.id, role_id=role_id)
                db.add(link)
        
        await db.commit()
        
        logger.info(
            "operator_user_created",
            user_id=str(user.id),
            email=data.email,
            is_super_admin=data.is_super_admin,
            role_count=len(data.role_ids),
            created_by=str(created_by) if created_by else None
        )
        
        return user, "Operator user created successfully"

    async def update_user(
        self,
        db: AsyncSession,
        user_id: UUID,
        data: OperatorUserUpdate,
        updated_by: Optional[UUID] = None
    ) -> Tuple[Optional[OperatorUser], str]:
        """Update an operator user."""
        user = await operator_user_repo.get_by_id(db, user_id)
        if not user:
            return None, "User not found"
        
        # Update fields
        if data.full_name is not None:
            user.full_name = data.full_name
        if data.phone is not None:
            user.phone = data.phone
        if data.is_active is not None:
            user.is_active = data.is_active
            logger.info(
                "operator_user_status_changed",
                user_id=str(user_id),
                is_active=data.is_active,
                updated_by=str(updated_by) if updated_by else None
            )
        
        await db.commit()
        
        # Invalidate cache
        await permission_resolver.invalidate_cache(user_id)
        
        return user, "User updated successfully"

    async def update_super_admin_status(
        self,
        db: AsyncSession,
        user_id: UUID,
        is_super_admin: bool,
        updated_by: Optional[UUID] = None
    ) -> Tuple[bool, str]:
        """Update super admin status (separate function for audit)."""
        user = await operator_user_repo.get_by_id(db, user_id)
        if not user:
            return False, "User not found"
        
        # Prevent removing super admin from yourself
        if updated_by == user_id and not is_super_admin:
            return False, "Cannot remove your own super admin status"
        
        user.is_super_admin = is_super_admin
        await db.commit()
        
        # Invalidate cache
        await permission_resolver.invalidate_cache(user_id)
        
        logger.warning(
            "operator_super_admin_changed",
            user_id=str(user_id),
            is_super_admin=is_super_admin,
            updated_by=str(updated_by) if updated_by else None
        )
        
        return True, "Super admin status updated"

    async def assign_roles_to_user(
        self,
        db: AsyncSession,
        user_id: UUID,
        role_ids: List[UUID],
        replace_existing: bool = False,
        assigned_by: Optional[UUID] = None
    ) -> Tuple[bool, str]:
        """Assign roles to an operator."""
        user = await operator_user_repo.get_by_id(db, user_id)
        if not user:
            return False, "User not found"
        
        # Validate all role IDs exist
        for role_id in role_ids:
            role = await role_repo.get_by_id(db, role_id)
            if not role:
                return False, f"Role not found: {role_id}"
        
        # Get current roles
        current_roles = await db.execute(
            select(UserRoleLink).where(UserRoleLink.user_id == user_id)
        )
        current_role_ids = {link.role_id for link in current_roles.scalars().all()}
        
        if replace_existing:
            # Remove all existing roles
            for role_id in list(current_role_ids):
                await db.execute(
                    delete(UserRoleLink).where(
                        and_(UserRoleLink.user_id == user_id, UserRoleLink.role_id == role_id)
                    )
                )
        
        # Add new roles (skip duplicates)
        new_roles_added = []
        for role_id in role_ids:
            if role_id not in current_role_ids:
                link = UserRoleLink(user_id=user_id, role_id=role_id)
                db.add(link)
                new_roles_added.append(str(role_id))
        
        await db.commit()
        
        # Invalidate cache
        await permission_resolver.invalidate_cache(user_id)
        
        logger.info(
            "operator_roles_assigned",
            user_id=str(user_id),
            role_ids=new_roles_added,
            replace_existing=replace_existing,
            assigned_by=str(assigned_by) if assigned_by else None
        )
        
        return True, f"Assigned {len(new_roles_added)} roles to user"

    async def remove_roles_from_user(
        self,
        db: AsyncSession,
        user_id: UUID,
        role_ids: List[UUID],
        removed_by: Optional[UUID] = None
    ) -> Tuple[bool, str]:
        """Remove roles from an operator."""
        from sqlalchemy import delete, and_
        
        user = await operator_user_repo.get_by_id(db, user_id)
        if not user:
            return False, "User not found"
        
        removed_count = 0
        for role_id in role_ids:
            result = await db.execute(
                delete(UserRoleLink).where(
                    and_(UserRoleLink.user_id == user_id, UserRoleLink.role_id == role_id)
                )
            )
            removed_count += result.rowcount
        
        await db.commit()
        
        # Invalidate cache
        await permission_resolver.invalidate_cache(user_id)
        
        logger.info(
            "operator_roles_removed",
            user_id=str(user_id),
            removed_count=removed_count,
            removed_by=str(removed_by) if removed_by else None
        )
        
        return True, f"Removed {removed_count} roles from user"

    async def assign_direct_permissions(
        self,
        db: AsyncSession,
        user_id: UUID,
        permissions: List[DirectPermissionAssignment],
        replace_existing: bool = False,
        assigned_by: Optional[UUID] = None
    ) -> Tuple[bool, str]:
        """Assign direct permission overrides to a user."""
        user = await operator_user_repo.get_by_id(db, user_id)
        if not user:
            return False, "User not found"
        
        # Validate permission codes
        valid_perms = PermissionEnum.all_permissions()
        for perm in permissions:
            if perm.permission_code not in valid_perms:
                return False, f"Invalid permission code: {perm.permission_code}"
        
        # Convert to dict format for repo
        perm_dicts = [
            {
                "permission_code": p.permission_code,
                "granted": p.granted,
                "reason": p.reason
            }
            for p in permissions
        ]
        
        await permission_override_repo.assign_permissions(
            db,
            user_id,
            perm_dicts,
            replace_existing,
            assigned_by
        )
        
        await db.commit()
        
        # Invalidate cache
        await permission_resolver.invalidate_cache(user_id)
        
        logger.info(
            "operator_direct_permissions_assigned",
            user_id=str(user_id),
            permission_count=len(permissions),
            replace_existing=replace_existing,
            assigned_by=str(assigned_by) if assigned_by else None
        )
        
        return True, "Direct permissions assigned successfully"

    async def remove_direct_permissions(
        self,
        db: AsyncSession,
        user_id: UUID,
        permission_codes: List[str],
        removed_by: Optional[UUID] = None
    ) -> Tuple[bool, str]:
        """Remove direct permission overrides from a user."""
        user = await operator_user_repo.get_by_id(db, user_id)
        if not user:
            return False, "User not found"
        
        count = await permission_override_repo.remove_overrides(db, user_id, permission_codes)
        await db.commit()
        
        # Invalidate cache
        await permission_resolver.invalidate_cache(user_id)
        
        logger.info(
            "operator_direct_permissions_removed",
            user_id=str(user_id),
            removed_count=count,
            removed_by=str(removed_by) if removed_by else None
        )
        
        return True, f"Removed {count} permission overrides"

    async def delete_user(
        self,
        db: AsyncSession,
        user_id: UUID,
        deleted_by: Optional[UUID] = None
    ) -> Tuple[bool, str]:
        """Delete an operator user."""
        user = await operator_user_repo.get_by_id(db, user_id)
        if not user:
            return False, "User not found"
        
        # Prevent self-deletion
        if deleted_by == user_id:
            return False, "Cannot delete your own account"
        
        await operator_user_repo.delete(db, user_id)
        
        # Invalidate cache
        await permission_resolver.invalidate_cache(user_id)
        
        logger.warning(
            "operator_user_deleted",
            user_id=str(user_id),
            email=user.email,
            deleted_by=str(deleted_by) if deleted_by else None
        )
        
        return True, "User deleted successfully"

    async def get_user_with_roles(
        self,
        db: AsyncSession,
        user_id: UUID
    ) -> Optional[OperatorUser]:
        """Get operator with roles loaded."""
        return await operator_user_repo.get_by_id_with_roles(db, user_id)

    async def get_user_with_permissions(
        self,
        db: AsyncSession,
        user_id: UUID
    ) -> Optional[OperatorUser]:
        """Get operator with roles and permissions loaded."""
        return await operator_user_repo.get_by_id_with_permissions(db, user_id)

    async def list_users(
        self,
        db: AsyncSession,
        is_active: Optional[bool] = None,
        is_super_admin: Optional[bool] = None,
        role_id: Optional[UUID] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 50
    ) -> Tuple[List[OperatorUser], int]:
        """List operator users with pagination."""
        return await operator_user_repo.list_operators(
            db, is_active, is_super_admin, role_id, search, page, page_size
        )


# Global instance
operator_user_service = OperatorUserService()
