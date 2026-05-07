"""
Operator User Repository

Database operations for OperatorUser model.
"""

from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from sqlalchemy import func, select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.operator_models.operator import OperatorUser, UserRoleLink, Role
from app.repositories.base import BaseRepository


class OperatorUserRepository(BaseRepository[OperatorUser]):
    """Repository for OperatorUser operations."""

    def __init__(self):
        super().__init__(OperatorUser)

    async def get_by_email(
        self,
        db: AsyncSession,
        email: str,
        include_roles: bool = False
    ) -> Optional[OperatorUser]:
        """Get operator by email (case-insensitive)."""
        query = select(OperatorUser).where(
            func.lower(OperatorUser.email) == email.lower()
        )
        
        if include_roles:
            query = query.options(
                selectinload(OperatorUser.role_links).selectinload(UserRoleLink.role)
            )
        
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_id_with_roles(
        self,
        db: AsyncSession,
        user_id: UUID
    ) -> Optional[OperatorUser]:
        """Get operator with roles eagerly loaded."""
        result = await db.execute(
            select(OperatorUser)
            .where(OperatorUser.id == user_id)
            .options(
                selectinload(OperatorUser.role_links).selectinload(UserRoleLink.role)
            )
        )
        return result.scalar_one_or_none()

    async def get_by_id_with_permissions(
        self,
        db: AsyncSession,
        user_id: UUID
    ) -> Optional[OperatorUser]:
        """Get operator with roles and permission overrides eagerly loaded."""
        result = await db.execute(
            select(OperatorUser)
            .where(OperatorUser.id == user_id)
            .options(
                selectinload(OperatorUser.role_links).selectinload(UserRoleLink.role),
                selectinload(OperatorUser.permission_overrides)
            )
        )
        return result.scalar_one_or_none()

    async def list_operators(
        self,
        db: AsyncSession,
        is_active: Optional[bool] = None,
        is_super_admin: Optional[bool] = None,
        role_id: Optional[UUID] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 50
    ) -> tuple[List[OperatorUser], int]:
        """List operators with filtering and pagination.
        
        Returns: (list of operators, total count)
        """
        # Build base query
        query = select(OperatorUser)
        
        # Apply filters
        conditions = []
        if is_active is not None:
            conditions.append(OperatorUser.is_active == is_active)
        if is_super_admin is not None:
            conditions.append(OperatorUser.is_super_admin == is_super_admin)
        if search:
            search_lower = f"%{search.lower()}%"
            conditions.append(
                or_(
                    func.lower(OperatorUser.full_name).like(search_lower),
                    func.lower(OperatorUser.email).like(search_lower)
                )
            )
        
        # Role filter requires join
        if role_id:
            query = query.join(
                UserRoleLink,
                OperatorUser.id == UserRoleLink.user_id
            ).where(UserRoleLink.role_id == role_id)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0
        
        # Apply pagination and load roles
        query = (
            query
            .options(selectinload(OperatorUser.role_links).selectinload(UserRoleLink.role))
            .offset((page - 1) * page_size)
            .limit(page_size)
            .order_by(OperatorUser.created_at.desc())
        )
        
        result = await db.execute(query)
        return list(result.scalars().all()), total

    async def update_last_login(
        self,
        db: AsyncSession,
        user_id: UUID,
        jti: str
    ) -> None:
        """Update last login time and current JTI."""
        user = await self.get_by_id(db, user_id)
        if user:
            user.last_login = datetime.now(timezone.utc)
            user.current_jti = jti
            await db.flush()

    async def increment_failed_attempts(
        self,
        db: AsyncSession,
        user_id: UUID
    ) -> OperatorUser:
        """Increment failed login attempts."""
        user = await self.get_by_id(db, user_id)
        if user:
            user.failed_login_attempts += 1
            # Lock account after 5 failed attempts for 30 minutes
            if user.failed_login_attempts >= 5:
                user.locked_until = datetime.now(timezone.utc).replace(minute=30)
            await db.flush()
        return user

    async def reset_failed_attempts(
        self,
        db: AsyncSession,
        user_id: UUID
    ) -> None:
        """Reset failed login attempts after successful login."""
        user = await self.get_by_id(db, user_id)
        if user:
            user.failed_login_attempts = 0
            user.locked_until = None
            await db.flush()

    async def set_password_reset_token(
        self,
        db: AsyncSession,
        user_id: UUID,
        token: str,
        expires: datetime
    ) -> None:
        """Set password reset token."""
        user = await self.get_by_id(db, user_id)
        if user:
            user.password_reset_token = token
            user.password_reset_expires = expires
            await db.flush()

    async def clear_password_reset_token(
        self,
        db: AsyncSession,
        user_id: UUID
    ) -> None:
        """Clear password reset token after use."""
        user = await self.get_by_id(db, user_id)
        if user:
            user.password_reset_token = None
            user.password_reset_expires = None
            await db.flush()

    async def verify_email(
        self,
        db: AsyncSession,
        user_id: UUID
    ) -> None:
        """Mark email as verified."""
        user = await self.get_by_id(db, user_id)
        if user:
            user.email_verified = True
            user.email_verified_at = datetime.now(timezone.utc)
            await db.flush()

    async def update_password(
        self,
        db: AsyncSession,
        user_id: UUID,
        password_hash: str
    ) -> None:
        """Update password hash."""
        user = await self.get_by_id(db, user_id)
        if user:
            user.password_hash = password_hash
            # Clear any reset tokens
            user.password_reset_token = None
            user.password_reset_expires = None
            await db.flush()

    async def email_exists(
        self,
        db: AsyncSession,
        email: str,
        exclude_user_id: Optional[UUID] = None
    ) -> bool:
        """Check if email is already registered."""
        query = select(OperatorUser).where(
            func.lower(OperatorUser.email) == email.lower()
        )
        if exclude_user_id:
            query = query.where(OperatorUser.id != exclude_user_id)
        
        result = await db.execute(query)
        return result.scalar_one_or_none() is not None


# Global instance
operator_user_repo = OperatorUserRepository()
