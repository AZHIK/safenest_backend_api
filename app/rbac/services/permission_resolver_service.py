"""
Permission Resolution Engine

This is the core RBAC permission resolution logic.
Computes effective permissions for operators based on:
1. Role-inherited permissions
2. Direct permission grants
3. Direct permission denies (overrides)
4. Super admin status (grants all permissions)

Uses Redis caching for performance.
"""

from typing import Set, Dict, List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.redis import redis_client
from app.operator_models.operator import OperatorUser, UserRoleLink, Role, RolePermissionLink
from app.operator_repositories.operator_user import operator_user_repo
from app.rbac.permission_enum import PermissionEnum

logger = get_logger(__name__)

# Cache TTL in seconds (5 minutes)
PERMISSION_CACHE_TTL = 300


class PermissionResolverService:
    """
    Permission Resolution Service
    
    Computes effective permissions for an operator user.
    Caches results in Redis for performance.
    """

    async def get_effective_permissions(
        self,
        db: AsyncSession,
        user_id: UUID,
        skip_cache: bool = False
    ) -> Set[str]:
        """
        Get effective permissions for an operator.
        
        Logic:
        1. If super_admin: return all permissions
        2. Start with union of all permissions from assigned roles
        3. Add directly granted permissions
        4. Remove directly denied permissions (DENY overrides GRANT)
        
        Args:
            db: Database session
            user_id: Operator user ID
            skip_cache: If True, bypass Redis cache
            
        Returns:
            Set of effective permission codes
        """
        # Try cache first
        if not skip_cache:
            cached = await self._get_cached_permissions(user_id)
            if cached is not None:
                logger.debug("permission_cache_hit", user_id=str(user_id))
                return cached
        
        # Load user with all permission-related data
        user = await operator_user_repo.get_by_id_with_permissions(db, user_id)
        if not user:
            logger.warning("permission_resolution_user_not_found", user_id=str(user_id))
            return set()
        
        # Check if super admin
        if user.is_super_admin:
            all_perms = PermissionEnum.all_permissions()
            await self._cache_permissions(user_id, all_perms)
            logger.info("super_admin_permissions_granted", user_id=str(user_id))
            return all_perms
        
        # Start with empty set
        effective_perms: Set[str] = set()
        
        # 1. Collect permissions from roles
        role_permissions = self._extract_role_permissions(user)
        effective_perms.update(role_permissions)
        
        # 2. Apply direct permission overrides
        direct_grants, direct_denies = self._extract_direct_overrides(user)
        
        # Add direct grants
        effective_perms.update(direct_grants)
        
        # Remove direct denies (DENY overrides everything)
        effective_perms.difference_update(direct_denies)
        
        # Cache result
        await self._cache_permissions(user_id, effective_perms)
        
        logger.debug(
            "permissions_resolved",
            user_id=str(user_id),
            total=len(effective_perms),
            from_roles=len(role_permissions),
            direct_grants=len(direct_grants),
            direct_denies=len(direct_denies)
        )
        
        return effective_perms

    async def get_permission_breakdown(
        self,
        db: AsyncSession,
        user_id: UUID
    ) -> Dict[str, List[str]]:
        """
        Get detailed permission breakdown for an operator.
        
        Returns dict with:
        - permissions: All effective permissions
        - role_derived: Permissions inherited from roles
        - direct_grants: Directly granted permissions
        - direct_denies: Directly denied permissions
        - is_super_admin: Whether user is super admin
        """
        user = await operator_user_repo.get_by_id_with_permissions(db, user_id)
        if not user:
            return {
                "permissions": [],
                "role_derived": [],
                "direct_grants": [],
                "direct_denies": [],
                "is_super_admin": False
            }
        
        if user.is_super_admin:
            all_perms = list(PermissionEnum.all_permissions())
            return {
                "permissions": all_perms,
                "role_derived": all_perms,
                "direct_grants": [],
                "direct_denies": [],
                "is_super_admin": True
            }
        
        # Extract from roles
        role_permissions = self._extract_role_permissions(user)
        
        # Extract direct overrides
        direct_grants, direct_denies = self._extract_direct_overrides(user)
        
        # Compute effective
        effective = set(role_permissions)
        effective.update(direct_grants)
        effective.difference_update(direct_denies)
        
        return {
            "permissions": sorted(list(effective)),
            "role_derived": sorted(list(role_permissions)),
            "direct_grants": sorted(list(direct_grants)),
            "direct_denies": sorted(list(direct_denies)),
            "is_super_admin": False
        }

    def _extract_role_permissions(self, user: OperatorUser) -> Set[str]:
        """Extract all permission codes from user's roles."""
        permissions: Set[str] = set()
        
        if not user.role_links:
            return permissions
        
        for user_role_link in user.role_links:
            role = user_role_link.role
            if role and role.permission_links:
                for perm_link in role.permission_links:
                    permissions.add(perm_link.permission_code)
        
        return permissions

    def _extract_direct_overrides(self, user: OperatorUser) -> tuple[Set[str], Set[str]]:
        """Extract direct permission grants and denies."""
        grants: Set[str] = set()
        denies: Set[str] = set()
        
        if not user.permission_overrides:
            return grants, denies
        
        for override in user.permission_overrides:
            if override.granted:
                grants.add(override.permission_code)
            else:
                denies.add(override.permission_code)
        
        return grants, denies

    async def has_permission(
        self,
        db: AsyncSession,
        user_id: UUID,
        permission_code: str
    ) -> bool:
        """Check if user has a specific permission."""
        effective = await self.get_effective_permissions(db, user_id)
        return permission_code in effective

    async def has_any_permission(
        self,
        db: AsyncSession,
        user_id: UUID,
        permission_codes: List[str]
    ) -> bool:
        """Check if user has any of the specified permissions."""
        if not permission_codes:
            return True
        effective = await self.get_effective_permissions(db, user_id)
        return any(p in effective for p in permission_codes)

    async def has_all_permissions(
        self,
        db: AsyncSession,
        user_id: UUID,
        permission_codes: List[str]
    ) -> bool:
        """Check if user has all of the specified permissions."""
        if not permission_codes:
            return True
        effective = await self.get_effective_permissions(db, user_id)
        return all(p in effective for p in permission_codes)

    # ============== Redis Cache Operations ==============

    async def _get_cached_permissions(
        self,
        user_id: UUID
    ) -> Optional[Set[str]]:
        """Get permissions from Redis cache."""
        try:
            cache_key = f"operator:permissions:{user_id}"
            cached = await redis_client.client.smembers(cache_key)
            if cached:
                # Decode bytes if necessary
                return {p.decode() if isinstance(p, bytes) else p for p in cached}
            return None
        except Exception as e:
            logger.error("permission_cache_get_error", user_id=str(user_id), error=str(e))
            return None

    async def _cache_permissions(
        self,
        user_id: UUID,
        permissions: Set[str]
    ) -> None:
        """Store permissions in Redis cache."""
        try:
            cache_key = f"operator:permissions:{user_id}"
            
            if permissions:
                pipe = redis_client.client.pipeline()
                await pipe.sadd(cache_key, *permissions)
                await pipe.expire(cache_key, PERMISSION_CACHE_TTL)
                await pipe.execute()
            else:
                # Store empty marker
                await redis_client.client.setex(cache_key, PERMISSION_CACHE_TTL, "empty")
                
            logger.debug("permission_cache_set", user_id=str(user_id), count=len(permissions))
        except Exception as e:
            logger.error("permission_cache_set_error", user_id=str(user_id), error=str(e))

    async def invalidate_cache(
        self,
        user_id: UUID
    ) -> None:
        """Invalidate permission cache for a user."""
        try:
            cache_key = f"operator:permissions:{user_id}"
            await redis_client.client.delete(cache_key)
            logger.debug("permission_cache_invalidate", user_id=str(user_id))
        except Exception as e:
            logger.error("permission_cache_invalidate_error", user_id=str(user_id), error=str(e))

    async def invalidate_cache_for_role(
        self,
        db: AsyncSession,
        role_id: UUID
    ) -> None:
        """Invalidate cache for all users with a specific role."""
        # Find all users with this role
        from sqlalchemy import select
        from app.operator_models.operator import UserRoleLink
        
        result = await db.execute(
            select(UserRoleLink.user_id).where(UserRoleLink.role_id == role_id)
        )
        user_ids = [row[0] for row in result.all()]
        
        # Invalidate cache for each user
        for user_id in user_ids:
            await self.invalidate_cache(user_id)
        
        logger.info("permission_cache_invalidated_for_role", role_id=str(role_id), user_count=len(user_ids))


# Global instance
permission_resolver = PermissionResolverService()
