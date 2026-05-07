"""
Role Repository

Database operations for Role and RolePermissionLink models.
"""

from typing import List, Optional
from uuid import UUID

from sqlalchemy import func, select, delete, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.operator_models.operator import Role, RolePermissionLink, UserRoleLink
from app.repositories.base import BaseRepository


class RoleRepository(BaseRepository[Role]):
    """Repository for Role operations."""

    def __init__(self):
        super().__init__(Role)

    async def get_by_name(
        self,
        db: AsyncSession,
        name: str
    ) -> Optional[Role]:
        """Get role by name (case-insensitive)."""
        result = await db.execute(
            select(Role).where(func.lower(Role.name) == name.lower())
        )
        return result.scalar_one_or_none()

    async def get_by_id_with_permissions(
        self,
        db: AsyncSession,
        role_id: UUID
    ) -> Optional[Role]:
        """Get role with permissions eagerly loaded."""
        result = await db.execute(
            select(Role)
            .where(Role.id == role_id)
            .options(selectinload(Role.permission_links))
        )
        return result.scalar_one_or_none()

    async def get_by_id_with_users(
        self,
        db: AsyncSession,
        role_id: UUID
    ) -> Optional[Role]:
        """Get role with user assignments eagerly loaded."""
        result = await db.execute(
            select(Role)
            .where(Role.id == role_id)
            .options(selectinload(Role.user_links))
        )
        return result.scalar_one_or_none()

    async def list_roles(
        self,
        db: AsyncSession,
        is_system: Optional[bool] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 50
    ) -> tuple[List[Role], int]:
        """List roles with filtering and pagination.
        
        Returns: (list of roles, total count)
        """
        query = select(Role)
        
        # Apply filters
        if is_system is not None:
            query = query.where(Role.is_system == is_system)
        if search:
            search_lower = f"%{search.lower()}%"
            query = query.where(
                func.lower(Role.name).like(search_lower) |
                func.lower(Role.description).like(search_lower)
            )
        
        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0
        
        # Apply pagination
        query = (
            query
            .offset((page - 1) * page_size)
            .limit(page_size)
            .order_by(Role.is_system.desc(), Role.name.asc())
        )
        
        result = await db.execute(query)
        return list(result.scalars().all()), total

    async def list_all_permissions(
        self,
        db: AsyncSession,
        role_id: UUID
    ) -> List[str]:
        """Get all permission codes assigned to a role."""
        result = await db.execute(
            select(RolePermissionLink.permission_code)
            .where(RolePermissionLink.role_id == role_id)
        )
        return [row[0] for row in result.all()]

    async def assign_permissions(
        self,
        db: AsyncSession,
        role_id: UUID,
        permission_codes: List[str],
        replace_existing: bool = False
    ) -> List[RolePermissionLink]:
        """Assign permissions to a role.
        
        If replace_existing=True, all existing permissions are removed first.
        Returns the created/updated permission links.
        """
        if replace_existing:
            # Delete all existing permissions
            await db.execute(
                delete(RolePermissionLink).where(
                    RolePermissionLink.role_id == role_id
                )
            )
        
        # Get existing permissions to avoid duplicates
        if not replace_existing:
            existing_result = await db.execute(
                select(RolePermissionLink.permission_code)
                .where(RolePermissionLink.role_id == role_id)
            )
            existing = {row[0] for row in existing_result.all()}
            permission_codes = [p for p in permission_codes if p not in existing]
        
        # Create new permission links
        created_links = []
        for code in permission_codes:
            link = RolePermissionLink(
                role_id=role_id,
                permission_code=code
            )
            db.add(link)
            created_links.append(link)
        
        await db.flush()
        return created_links

    async def remove_permissions(
        self,
        db: AsyncSession,
        role_id: UUID,
        permission_codes: List[str]
    ) -> int:
        """Remove permissions from a role.
        
        Returns number of permissions removed.
        """
        result = await db.execute(
            delete(RolePermissionLink).where(
                and_(
                    RolePermissionLink.role_id == role_id,
                    RolePermissionLink.permission_code.in_(permission_codes)
                )
            )
        )
        return result.rowcount

    async def get_role_user_count(
        self,
        db: AsyncSession,
        role_id: UUID
    ) -> int:
        """Get number of users assigned to this role."""
        result = await db.execute(
            select(func.count()).where(UserRoleLink.role_id == role_id)
        )
        return result.scalar() or 0

    async def get_role_permission_count(
        self,
        db: AsyncSession,
        role_id: UUID
    ) -> int:
        """Get number of permissions assigned to this role."""
        result = await db.execute(
            select(func.count()).where(RolePermissionLink.role_id == role_id)
        )
        return result.scalar() or 0

    async def name_exists(
        self,
        db: AsyncSession,
        name: str,
        exclude_role_id: Optional[UUID] = None
    ) -> bool:
        """Check if role name already exists."""
        query = select(Role).where(func.lower(Role.name) == name.lower())
        if exclude_role_id:
            query = query.where(Role.id != exclude_role_id)
        
        result = await db.execute(query)
        return result.scalar_one_or_none() is not None


# Global instance
role_repo = RoleRepository()
