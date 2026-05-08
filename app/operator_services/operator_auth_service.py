"""
Operator Authentication Service

Separate JWT-based authentication for institutional operators.
Do NOT mix with survivor mobile app authentication.
"""

import secrets
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple
from uuid import UUID

from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.security import get_password_hash, verify_password
from app.db.redis import redis_client
from app.operator_models.operator import OperatorUser
from app.operator_repositories.operator_user import operator_user_repo
from app.operator_schemas.auth import OperatorTokenResponse

settings = get_settings()
logger = get_logger(__name__)

# Separate token expiry for operators
OPERATOR_ACCESS_TOKEN_EXPIRE_MINUTES = 60  # 1 hour
OPERATOR_REFRESH_TOKEN_EXPIRE_DAYS = 7  # 7 days


class OperatorAuthService:
    """Authentication service for operator users."""

    def __init__(self):
        self.algorithm = settings.jwt_algorithm
        self.secret_key = settings.jwt_secret_key

    def _hash_password(self, password: str) -> str:
        """Hash a password using the shared password context."""
        return get_password_hash(password)

    def _verify_password(self, password: str, password_hash: str) -> bool:
        """Verify a password against its hash."""
        return verify_password(password, password_hash)

    def _create_token(
        self,
        user_id: UUID,
        token_type: str,
        expires_delta: timedelta,
        jti: Optional[str] = None
    ) -> Tuple[str, str, datetime]:
        """Create a JWT token.
        
        Returns: (token, jti, expiry)
        """
        now = datetime.now(timezone.utc)
        expire = now + expires_delta
        
        if jti is None:
            jti = secrets.token_urlsafe(32)
        
        payload = {
            "sub": str(user_id),
            "jti": jti,
            "type": token_type,
            "domain": "operator",  # Critical: separates from survivor auth
            "iat": now,
            "exp": expire,
        }
        
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        return token, jti, expire

    async def authenticate(
        self,
        db: AsyncSession,
        email: str,
        password: str
    ) -> Optional[OperatorUser]:
        """Authenticate an operator by email and password."""
        user = await operator_user_repo.get_by_email(db, email, include_roles=True)
        
        if not user:
            logger.warning("operator_auth_failed", email=email, reason="user_not_found")
            return None
        
        if not user.is_active:
            logger.warning("operator_auth_failed", email=email, reason="account_inactive")
            return None
        
        if user.is_locked:
            logger.warning("operator_auth_failed", email=email, reason="account_locked")
            return None
        
        if not self._verify_password(password, user.password_hash):
            # Increment failed attempts
            await operator_user_repo.increment_failed_attempts(db, user.id)
            logger.warning("operator_auth_failed", email=email, reason="invalid_password")
            return None
        
        # Reset failed attempts on success
        await operator_user_repo.reset_failed_attempts(db, user.id)
        
        return user

    async def login(
        self,
        db: AsyncSession,
        email: str,
        password: str
    ) -> Optional[OperatorTokenResponse]:
        """Authenticate and generate tokens."""
        user = await self.authenticate(db, email, password)
        
        if not user:
            return None
        
        # Generate tokens
        access_token, access_jti, access_exp = self._create_token(
            user.id,
            "access",
            timedelta(minutes=OPERATOR_ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        
        refresh_token, refresh_jti, refresh_exp = self._create_token(
            user.id,
            "refresh",
            timedelta(days=OPERATOR_REFRESH_TOKEN_EXPIRE_DAYS)
        )
        
        # Update last login
        await operator_user_repo.update_last_login(db, user.id, access_jti)
        
        # Store refresh token in Redis for revocation capability
        await redis_client.client.setex(
            f"operator:refresh:{refresh_jti}",
            int(timedelta(days=OPERATOR_REFRESH_TOKEN_EXPIRE_DAYS).total_seconds()),
            str(user.id)
        )
        
        logger.info("operator_login_success", user_id=str(user.id), email=email)
        
        return OperatorTokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=int(timedelta(minutes=OPERATOR_ACCESS_TOKEN_EXPIRE_MINUTES).total_seconds()),
            refresh_expires_in=int(timedelta(days=OPERATOR_REFRESH_TOKEN_EXPIRE_DAYS).total_seconds())
        )

    async def refresh_token(
        self,
        db: AsyncSession,
        refresh_token: str
    ) -> Optional[OperatorTokenResponse]:
        """Refresh access token using refresh token."""
        try:
            payload = jwt.decode(
                refresh_token,
                self.secret_key,
                algorithms=[self.algorithm]
            )
            
            # Validate token type and domain
            if payload.get("type") != "refresh":
                logger.warning("operator_refresh_failed", reason="invalid_token_type")
                return None
            
            if payload.get("domain") != "operator":
                logger.warning("operator_refresh_failed", reason="wrong_domain")
                return None
            
            user_id = UUID(payload.get("sub"))
            jti = payload.get("jti")
            
            # Check if refresh token is revoked
            stored = await redis_client.client.get(f"operator:refresh:{jti}")
            if not stored:
                logger.warning("operator_refresh_failed", reason="token_revoked")
                return None
            
            # Get user
            user = await operator_user_repo.get_by_id(db, user_id)
            if not user or not user.is_active:
                logger.warning("operator_refresh_failed", reason="user_inactive")
                return None
            
            # Generate new tokens
            new_access_token, new_access_jti, _ = self._create_token(
                user.id,
                "access",
                timedelta(minutes=OPERATOR_ACCESS_TOKEN_EXPIRE_MINUTES)
            )
            
            new_refresh_token, new_refresh_jti, _ = self._create_token(
                user.id,
                "refresh",
                timedelta(days=OPERATOR_REFRESH_TOKEN_EXPIRE_DAYS)
            )
            
            # Revoke old refresh token
            await redis_client.client.delete(f"operator:refresh:{jti}")
            
            # Store new refresh token
            await redis_client.client.setex(
                f"operator:refresh:{new_refresh_jti}",
                int(timedelta(days=OPERATOR_REFRESH_TOKEN_EXPIRE_DAYS).total_seconds()),
                str(user.id)
            )
            
            # Update current JTI
            await operator_user_repo.update_last_login(db, user.id, new_access_jti)
            
            logger.info("operator_token_refreshed", user_id=str(user.id))
            
            return OperatorTokenResponse(
                access_token=new_access_token,
                refresh_token=new_refresh_token,
                token_type="bearer",
                expires_in=int(timedelta(minutes=OPERATOR_ACCESS_TOKEN_EXPIRE_MINUTES).total_seconds()),
                refresh_expires_in=int(timedelta(days=OPERATOR_REFRESH_TOKEN_EXPIRE_DAYS).total_seconds())
            )
            
        except JWTError as e:
            logger.warning("operator_refresh_failed", reason="jwt_error", error=str(e))
            return None

    async def logout(
        self,
        db: AsyncSession,
        user_id: UUID,
        jti: Optional[str] = None
    ) -> bool:
        """Logout operator by revoking tokens."""
        try:
            # Clear current JTI
            user = await operator_user_repo.get_by_id(db, user_id)
            if user:
                user.current_jti = None
                await db.flush()
            
            # If JTI provided, blacklist it
            if jti:
                await redis_client.client.setex(
                    f"operator:blacklist:{jti}",
                    int(timedelta(hours=24).total_seconds()),
                    "revoked"
                )
            
            logger.info("operator_logout", user_id=str(user_id))
            return True
        except Exception as e:
            logger.error("operator_logout_failed", user_id=str(user_id), error=str(e))
            return False

    async def verify_access_token(
        self,
        token: str
    ) -> Optional[dict]:
        """Verify an access token and return payload."""
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm]
            )
            
            # Validate token type and domain
            if payload.get("type") != "access":
                return None
            
            if payload.get("domain") != "operator":
                return None
            
            # Check if token is revoked
            jti = payload.get("jti")
            if jti:
                blacklisted = await redis_client.client.get(f"operator:blacklist:{jti}")
                if blacklisted:
                    return None
            
            return payload
            
        except JWTError:
            return None

    def create_user(
        self,
        full_name: str,
        email: str,
        password: str,
        phone: Optional[str] = None,
        is_super_admin: bool = False
    ) -> OperatorUser:
        """Create a new operator user (does not commit to DB)."""
        return OperatorUser(
            id=uuid.uuid4(),
            full_name=full_name,
            email=email,
            phone=phone,
            password_hash=self._hash_password(password),
            is_active=True,
            is_super_admin=is_super_admin,
            failed_login_attempts=0,
            email_verified=False
        )

    async def change_password(
        self,
        db: AsyncSession,
        user_id: UUID,
        current_password: str,
        new_password: str
    ) -> Tuple[bool, str]:
        """Change user password.
        
        Returns: (success, message)
        """
        user = await operator_user_repo.get_by_id(db, user_id)
        if not user:
            return False, "User not found"
        
        if not self._verify_password(current_password, user.password_hash):
            return False, "Current password is incorrect"
        
        # Hash new password and update
        user.password_hash = self._hash_password(new_password)
        
        # Revoke all existing tokens
        if user.current_jti:
            await redis_client.client.setex(
                f"operator:blacklist:{user.current_jti}",
                int(timedelta(hours=24).total_seconds()),
                "revoked"
            )
        user.current_jti = None
        
        await db.flush()
        
        logger.info("operator_password_changed", user_id=str(user_id))
        return True, "Password changed successfully"

    async def set_password_reset_token(
        self,
        db: AsyncSession,
        user_id: UUID,
        token: str,
        expires: datetime
    ) -> bool:
        """Set password reset token for user."""
        try:
            await operator_user_repo.set_password_reset_token(db, user_id, token, expires)
            return True
        except Exception as e:
            logger.error("set_password_reset_token_failed", user_id=str(user_id), error=str(e))
            return False

    async def reset_password(
        self,
        db: AsyncSession,
        user_id: UUID,
        new_password: str
    ) -> bool:
        """Reset user password (admin action)."""
        try:
            new_hash = self._hash_password(new_password)
            await operator_user_repo.update_password(db, user_id, new_hash)
            
            logger.info("operator_password_reset", user_id=str(user_id))
            return True
        except Exception as e:
            logger.error("operator_password_reset_failed", user_id=str(user_id), error=str(e))
            return False


# Global instance
operator_auth_service = OperatorAuthService()
