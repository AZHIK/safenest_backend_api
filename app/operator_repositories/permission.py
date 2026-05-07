"""
Permission Override Repository

Database operations for UserPermissionOverride model.
"""

from typing import List, Optional
from uuid import UUID

from sqlalchemy import delete, and_, select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.operator_models.operator import UserPermissionOverride, UserRoleLink
from app.repositories.base import BaseRepository


class PermissionOverrideRepository(BaseRepository[UserPermissionOverride]):
    """Repository for UserPermissionOverride operations."""

    def __init__(self):
        super().__init__(UserPermissionOverride)

    async def get_user_overrides(
        self,
        db: AsyncSession,
        user_id: UUID
    ) -> List[UserPermissionOverride]:
        """Get all permission overrides for a user."""
        result = await db.execute(
            select(UserPermissionOverride)
            .where(UserPermissionOverride.user_id == user_id)
            .order_by(UserPermissionOverride.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_user_override(
        self,
        db: AsyncSession,
        user_id: UUID,
        permission_code: str
    ) -> Optional[UserPermissionOverride]:
        """Get specific permission override for a user."""
        result = await db.execute(
            select(UserPermissionOverride).where(
                and_(
                    UserPermissionOverride.user_id == user_id,
                    UserPermissionOverride.permission_code == permission_code
                )
            )
        )
        return result.scalar_one_or_none()

    async def set_override(
        self,
        db: AsyncSession,
        user_id: UUID,
        permission_code: str,
        granted: bool,
        reason: Optional[str] = None,
        created_by: Optional[UUID] = None
    ) -> UserPermissionOverride:
        """Set or update a permission override for a user.
        
        Creates new override if doesn't exist, updates existing one.
        """
        # Check if override already exists
        existing = await self.get_user_override(db, user_id, permission_code)
        
        if existing:
            # Update existing
            existing.granted = granted
            if reason:
                existing.reason = reason
            await db.flush()
            return existing
        else:
            # Create new
            override = UserPermissionOverride(
                user_id=user_id,
                permission_code=permission_code,
                granted=granted,
                reason=reason,
                created_by=created_by
            )
            db.add(override)
            await db.flush()
            return override

    async def assign_permissions(
        self,
        db: AsyncSession,
        user_id: UUID,
        permissions: List[dict],
        replace_existing: bool = False,
        created_by: Optional[UUID] = None
    ) -> List[UserPermissionOverride]:
        """Assign multiple permission overrides.
        
        Each permission dict should have:
        - permission_code: str
        - granted: bool
        - reason: Optional[str]
        """
        if replace_existing:
            # Delete all existing overrides
            await db.execute(
                delete(UserPermissionOverride).where(
                    UserPermissionOverride.user_id == user_id
                )
            )
        
        created_overrides = []
        for perm in permissions:
            override = await self.set_override(
                db,
                user_id,
                perm["permission_code"],
                perm["granted"],
                perm.get("reason"),
                created_by
            )
            created_overrides.append(override)
        
        return created_overrides

    async def remove_override(
        self,
        db: AsyncSession,
        user_id: UUID,
        permission_code: str
    ) -> bool:
        """Remove a specific permission override."""
        result = await db.execute(
            delete(UserPermissionOverride).where(
                and_(
                    UserPermissionOverride.user_id == user_id,
                    UserPermissionOverride.permission_code == permission_code
                )
            )
        )
        return result.rowcount > 0

    async def remove_overrides(
        self,
        db: AsyncSession,
        user_id: UUID,
        permission_codes: List[str]
    ) -> int:
        """Remove multiple permission overrides.
        
        Returns number of overrides removed.
        """
        result = await db.execute(
            delete(UserPermissionOverride).where(
                and_(
                    UserPermissionOverride.user_id == user_id,
                    UserPermissionOverride.permission_code.in_(permission_codes)
                )
            )
        )
        return result.rowcount

    async def clear_all_overrides(
        self,
        db: AsyncSession,
        user_id: UUID
    ) -> int:
        """Remove all permission overrides for a user.
        
        Returns number of overrides removed.
        """
        result = await db.execute(
            delete(UserPermissionOverride).where(
                UserPermissionOverride.user_id == user_id
            )
        )
        return result.rowcount

    async def get_user_override_count(
        self,
        db: AsyncSession,
        user_id: UUID
    ) -> int:
        """Get number of permission overrides for a user."""
        result = await db.execute(
            select(func.count()).where(
                UserPermissionOverride.user_id == user_id
            )
        )
        return result.scalar() or 0

    async def get_granted_overrides(
        self,
        db: AsyncSession,
        user_id: UUID
    ) -> List[str]:
        """Get list of granted permission codes."""
        result = await db.execute(
            select(UserPermissionOverride.permission_code)
            .where(
                and_(
                    UserPermissionOverride.user_id == user_id,
                    UserPermissionOverride.granted == True
                )
            )
        )
        return [row[0] for row in result.all()]

    async def get_denied_overrides(
        self,
        db: AsyncSession,
        user_id: UUID
    ) -> List[str]:
        """Get list of denied permission codes."""
        result = await db.execute(
            select(UserPermissionOverride.permission_code)
            .where(
                and_(
                    UserPermissionOverride.user_id == user_id,
                    UserPermissionOverride.granted == False
                )
            )
        )
        return [row[0] for row in result.all()]


# Global instance
permission_override_repo = PermissionOverrideRepository()
