from typing import Optional
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.user import User, AnonymousSession, TrustedContact, OTPCode
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self):
        super().__init__(User)

    async def get_by_phone(self, db: AsyncSession, phone: str) -> Optional[User]:
        result = await db.execute(
            select(User)
            .options(selectinload(User.trusted_contacts))
            .where(User.phone_number == phone)
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, db: AsyncSession, id: UUID) -> Optional[User]:
        result = await db.execute(
            select(User)
            .options(selectinload(User.trusted_contacts))
            .where(User.id == id)
        )
        return result.scalar_one_or_none()

    async def get_by_anonymous_session(
        self,
        db: AsyncSession,
        session_token: str
    ) -> Optional[User]:
        result = await db.execute(
            select(User)
            .options(selectinload(User.trusted_contacts))
            .join(AnonymousSession, User.id == AnonymousSession.user_id)
            .where(AnonymousSession.session_token == session_token)
        )
        return result.scalar_one_or_none()

    async def update_last_login(self, db: AsyncSession, user_id: UUID) -> None:
        from datetime import datetime, timezone
        await db.execute(
            update(User)
            .where(User.id == user_id)
            .values(last_login_at=datetime.now(timezone.utc))
        )
        await db.flush()


class AnonymousSessionRepository(BaseRepository[AnonymousSession]):
    def __init__(self):
        super().__init__(AnonymousSession)

    async def get_by_token(self, db: AsyncSession, token: str) -> Optional[AnonymousSession]:
        result = await db.execute(
            select(AnonymousSession).where(AnonymousSession.session_token == token)
        )
        return result.scalar_one_or_none()

    async def get_active_by_user(self, db: AsyncSession, user_id: UUID) -> list[AnonymousSession]:
        from datetime import datetime, timezone
        result = await db.execute(
            select(AnonymousSession)
            .where(
                AnonymousSession.user_id == user_id,
                AnonymousSession.expires_at > datetime.now(timezone.utc)
            )
        )
        return result.scalars().all()


class TrustedContactRepository(BaseRepository[TrustedContact]):
    def __init__(self):
        super().__init__(TrustedContact)

    async def get_by_user(self, db: AsyncSession, user_id: UUID) -> list[TrustedContact]:
        result = await db.execute(
            select(TrustedContact)
            .where(TrustedContact.user_id == user_id)
            .order_by(TrustedContact.priority, TrustedContact.created_at)
        )
        return result.scalars().all()

    async def get_primary_for_user(self, db: AsyncSession, user_id: UUID) -> Optional[TrustedContact]:
        result = await db.execute(
            select(TrustedContact)
            .where(
                TrustedContact.user_id == user_id,
                TrustedContact.priority == 1
            )
        )
        return result.scalar_one_or_none()


class OTPCodeRepository(BaseRepository[OTPCode]):
    def __init__(self):
        super().__init__(OTPCode)

    async def get_latest_for_phone(
        self,
        db: AsyncSession,
        phone: str,
        purpose: str = "auth"
    ) -> Optional[OTPCode]:
        result = await db.execute(
            select(OTPCode)
            .where(
                OTPCode.phone_number == phone,
                OTPCode.purpose == purpose,
                OTPCode.used_at.is_(None)
            )
            .order_by(OTPCode.created_at.desc())
        )
        return result.scalar_one_or_none()


user_repo = UserRepository()
anonymous_session_repo = AnonymousSessionRepository()
trusted_contact_repo = TrustedContactRepository()
otp_code_repo = OTPCodeRepository()
