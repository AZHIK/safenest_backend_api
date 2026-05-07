"""
Operator Authentication & Authorization Dependencies

FastAPI dependencies for:
- JWT validation (operator domain)
- Permission checking
- Current user injection

Do NOT mix with survivor mobile app dependencies.
"""

from typing import Callable, List, Optional
from uuid import UUID

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import security_logger
from app.db.database import get_db
from app.operator_models.operator import OperatorUser
from app.operator_repositories.operator_user import operator_user_repo
from app.operator_services.operator_auth_service import operator_auth_service
from app.rbac.permission_enum import PermissionEnum
from app.rbac.services.permission_resolver_service import permission_resolver

# Separate security scheme for operators
operator_security_scheme = HTTPBearer(auto_error=False, scheme_name="OperatorBearer")


async def get_current_operator(
    credentials: HTTPAuthorizationCredentials = Security(operator_security_scheme),
    db: AsyncSession = Depends(get_db)
) -> OperatorUser:
    """
    Dependency to get current authenticated operator.
    
    Validates:
    - Token is present and valid
    - Domain is 'operator' (not survivor)
    - Token not revoked/blacklisted
    - User exists and is active
    - User account not locked
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    
    # Verify token (this checks domain='operator' internally)
    payload = await operator_auth_service.verify_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Get user ID from token
    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        user_id = UUID(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID in token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Load user and roles eagerly so route handlers can serialize the operator
    # without triggering lazy async ORM IO during attribute access.
    user = await operator_user_repo.get_by_id_with_roles(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check account status
    if not user.is_active:
        security_logger.log_suspicious_activity(
            user_id=str(user.id),
            activity="inactive_operator_access_attempt"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive"
        )
    
    # Check if locked
    if user.is_locked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Account is locked until {user.locked_until}"
        )
    
    return user


async def get_optional_operator(
    credentials: HTTPAuthorizationCredentials = Security(operator_security_scheme),
    db: AsyncSession = Depends(get_db)
) -> Optional[OperatorUser]:
    """Dependency for optional operator authentication."""
    if not credentials:
        return None
    
    try:
        return await get_current_operator(credentials, db)
    except HTTPException:
        return None


class PermissionChecker:
    """
    Permission checker dependency factory.
    
    Usage:
        @router.get("/cases")
        async def list_cases(
            user: OperatorUser = Depends(require_permission("cases.view"))
        ):
            ...
    """
    
    def __init__(
        self,
        permission_codes: List[str],
        require_all: bool = True  # True=ALL required, False=ANY required
    ):
        self.permission_codes = permission_codes
        self.require_all = require_all
        
        # Validate permissions exist
        valid_perms = PermissionEnum.all_permissions()
        for code in permission_codes:
            if code not in valid_perms:
                raise ValueError(f"Invalid permission code: {code}")
    
    async def __call__(
        self,
        user: OperatorUser = Depends(get_current_operator),
        db: AsyncSession = Depends(get_db)
    ) -> OperatorUser:
        """Check permissions and return user if authorized."""
        # Super admin bypass
        if user.is_super_admin:
            return user
        
        # Get effective permissions
        effective_perms = await permission_resolver.get_effective_permissions(db, user.id)
        
        # Check permissions
        if self.require_all:
            # Must have ALL permissions
            missing = [p for p in self.permission_codes if p not in effective_perms]
            if missing:
                security_logger.log_suspicious_activity(
                    user_id=str(user.id),
                    activity="permission_denied",
                    details={"required": self.permission_codes, "missing": missing}
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Missing required permissions: {', '.join(missing)}"
                )
        else:
            # Must have ANY permission
            has_any = any(p in effective_perms for p in self.permission_codes)
            if not has_any:
                security_logger.log_suspicious_activity(
                    user_id=str(user.id),
                    activity="permission_denied",
                    details={"required_any": self.permission_codes}
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions for this action"
                )
        
        return user


# Convenience factory functions
def require_operator_permission(permission_code: str) -> Callable:
    """
    Factory to create a dependency that requires a specific permission.
    
    Usage:
        @router.get("/cases")
        async def list_cases(
            user: OperatorUser = Depends(require_operator_permission("cases.view"))
        ):
            ...
    """
    return PermissionChecker([permission_code], require_all=True)


def require_any_operator_permission(*permission_codes: str) -> Callable:
    """
    Factory to create a dependency that requires ANY of the specified permissions.
    
    Usage:
        @router.get("/reports")
        async def view_reports(
            user: OperatorUser = Depends(require_any_operator_permission(
                "cases.view", "analytics.view"
            ))
        ):
            ...
    """
    return PermissionChecker(list(permission_codes), require_all=False)


def require_all_operator_permissions(*permission_codes: str) -> Callable:
    """
    Factory to create a dependency that requires ALL of the specified permissions.
    
    Usage:
        @router.post("/admin-action")
        async def admin_action(
            user: OperatorUser = Depends(require_all_operator_permissions(
                "users.manage", "roles.manage"
            ))
        ):
            ...
    """
    return PermissionChecker(list(permission_codes), require_all=True)


# Predefined permission checkers for common operations
require_super_admin = PermissionChecker(["super_admin.access"], require_all=True)


# Super admin bypass checker
class SuperAdminChecker:
    """Checks if user is super admin."""
    
    async def __call__(
        self,
        user: OperatorUser = Depends(get_current_operator)
    ) -> OperatorUser:
        if not user.is_super_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Super admin access required"
            )
        return user


require_operator_super_admin = SuperAdminChecker()


async def check_operator_permission(
    db: AsyncSession,
    user: OperatorUser,
    permission_code: str
) -> bool:
    """Utility function to check if operator has a permission (for use in services)."""
    if user.is_super_admin:
        return True
    
    effective_perms = await permission_resolver.get_effective_permissions(db, user.id)
    return permission_code in effective_perms
