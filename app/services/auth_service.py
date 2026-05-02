from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import security_logger
from app.core.security import (
    generate_anonymous_session_id,
    generate_otp,
    token_manager,
    get_password_hash,
)
from app.db.redis import otp_storage, session_cache
from app.models.user import User, AnonymousSession, UserStatus
from app.repositories.user import user_repo, anonymous_session_repo
from app.schemas.auth import (
    OTPRequest,
    OTPVerify,
    AnonymousSessionCreate,
)

settings = get_settings()


class AuthService:
    def __init__(self):
        self.otp_expiry = settings.otp_expiry_minutes

    async def request_otp(self, db: AsyncSession, data: OTPRequest, ip: str = None) -> dict:
        phone = f"{data.country_code}{data.phone_number}"

        # Generate OTP
        otp = generate_otp(settings.otp_length)

        # Store in Redis
        await otp_storage.store(phone, otp, self.otp_expiry)

        # Log attempt (without OTP)
        security_logger.log_auth_attempt(phone, success=True, ip=ip, reason="otp_requested")

        # TODO: Send via SMS provider (Twilio, etc.)
        # For development, return OTP (DO NOT DO THIS IN PRODUCTION)
        if settings.is_testing or settings.debug:
            return {
                "message": "OTP sent successfully",
                "expires_in_seconds": self.otp_expiry * 60,
                "dev_otp": otp  # Only for development
            }

        return {
            "message": "OTP sent successfully",
            "expires_in_seconds": self.otp_expiry * 60
        }

    async def verify_otp(
        self,
        db: AsyncSession,
        data: OTPVerify,
        ip: str = None,
        user_agent: str = None
    ) -> Tuple[str, str, int, User]:
        """Verify OTP and return (access_token, refresh_token, expires_in, user_orm)."""
        phone = f"{data.country_code or '+1'}{data.phone_number}"

        # Verify OTP
        verified = await otp_storage.verify(phone, data.otp_code)
        if not verified:
            security_logger.log_auth_attempt(phone, success=False, ip=ip, reason="invalid_otp")
            raise ValueError("Invalid or expired OTP")

        # Get or create user (with eager-loaded trusted_contacts)
        user = await user_repo.get_by_phone(db, phone)
        is_new_user = False

        if not user:
            user = await self._create_verified_user(db, phone, data.country_code or '+1')
            is_new_user = True
        else:
            if not user.is_verified:
                user.is_verified = True
                await db.flush()

        # Update last login (this modifies the user)
        await user_repo.update_last_login(db, user.id)

        # Always reload with eager-loaded trusted_contacts to ensure fresh data
        # and guarantee no lazy loading during serialization
        user = await user_repo.get_by_id(db, user.id)

        # Create tokens
        access_token, refresh_token = token_manager.create_token_pair(
            str(user.id),
            phone,
            is_anonymous=False
        )

        security_logger.log_auth_attempt(phone, success=True, ip=ip, reason="login_success")

        return (
            access_token,
            refresh_token,
            settings.jwt_access_token_expire_minutes * 60,
            user
        )

    async def create_anonymous_session(
        self,
        db: AsyncSession,
        data: AnonymousSessionCreate,
        ip: str = None
    ) -> Tuple[str, User, datetime]:
        """Create anonymous session and return (session_token, user_orm, expires_at)."""
        # Create anonymous user
        user_data = {
            "is_anonymous": True,
            "is_verified": False,
            "status": UserStatus.ANONYMOUS,
            "language_preference": data.language_preference
        }
        user = await user_repo.create(db, user_data)
        # Reload with eager-loaded trusted_contacts
        user = await user_repo.get_by_id(db, user.id)

        # Create session
        session_token = generate_anonymous_session_id()
        expires_at = datetime.now(timezone.utc) + timedelta(days=30)

        session_data = {
            "session_token": session_token,
            "user_id": user.id,
            "device_fingerprint": data.device_fingerprint,
            "ip_address": ip,
            "expires_at": expires_at
        }
        await anonymous_session_repo.create(db, session_data)

        # Cache session in Redis
        await session_cache.store(
            session_token,
            {"user_id": str(user.id), "ip": ip},
            expire_hours=24 * 30
        )

        security_logger.log_auth_attempt(
            "anonymous",
            success=True,
            ip=ip,
            reason="anonymous_session_created"
        )

        return (session_token, user, expires_at)

    async def refresh_token(self, refresh_token: str) -> Tuple[str, str, int, dict]:
        """Refresh token and return (access_token, refresh_token, expires_in, user_dict)."""
        payload = token_manager.verify_refresh_token(refresh_token)
        if not payload:
            raise ValueError("Invalid refresh token")

        user_id = payload.get("sub")
        phone = payload.get("phone")
        is_anonymous = payload.get("anonymous", False)

        # Issue new token pair
        new_access, new_refresh = token_manager.create_token_pair(
            user_id,
            phone,
            is_anonymous
        )

        # Create a minimal user dict (not ORM model since we don't hit DB)
        user_dict = {
            "id": UUID(user_id),
            "phone_number": None if is_anonymous else phone,
            "is_anonymous": is_anonymous,
            "is_verified": not is_anonymous,
            "language_preference": "en",
            "status": "anonymous" if is_anonymous else "active",
            "created_at": datetime.now(timezone.utc)
        }

        return (
            new_access,
            new_refresh,
            settings.jwt_access_token_expire_minutes * 60,
            user_dict
        )

    async def get_current_user(self, db: AsyncSession, user_id: UUID) -> Optional[User]:
        """Get current user as ORM model (with trusted_contacts eager-loaded)."""
        return await user_repo.get_by_id(db, user_id)

    async def _create_verified_user(
        self,
        db: AsyncSession,
        phone: str,
        country_code: str
    ) -> User:
        user_data = {
            "phone_number": phone,
            "country_code": country_code,
            "is_verified": True,
            "is_anonymous": False,
            "status": UserStatus.ACTIVE
        }
        return await user_repo.create(db, user_data)


auth_service = AuthService()
