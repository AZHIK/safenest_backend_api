from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, update, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.messaging import Conversation, ConversationParticipant, Message, MessageStatus
from app.repositories.base import BaseRepository


class ConversationRepository(BaseRepository[Conversation]):
    def __init__(self):
        super().__init__(Conversation)

    async def get_by_id_with_participants(
        self,
        db: AsyncSession,
        conversation_id: UUID
    ) -> Optional[Conversation]:
        result = await db.execute(
            select(Conversation)
            .options(selectinload(Conversation.participants))
            .where(Conversation.id == conversation_id)
        )
        return result.scalar_one_or_none()

    async def get_for_user(
        self,
        db: AsyncSession,
        user_id: UUID,
        skip: int = 0,
        limit: int = 20
    ) -> List[Conversation]:
        result = await db.execute(
            select(Conversation)
            .options(selectinload(Conversation.participants))
            .join(ConversationParticipant)
            .where(
                ConversationParticipant.user_id == user_id,
                ConversationParticipant.left_at.is_(None)
            )
            .order_by(Conversation.last_message_at.desc().nullslast())
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def get_direct_conversation(
        self,
        db: AsyncSession,
        user1_id: UUID,
        user2_id: UUID
    ) -> Optional[Conversation]:
        # Find conversation where both users are participants (direct only)
        from sqlalchemy import func
        result = await db.execute(
            select(Conversation)
            .options(selectinload(Conversation.participants))
            .join(ConversationParticipant, Conversation.id == ConversationParticipant.conversation_id)
            .where(
                Conversation.conversation_type == "direct",
                ConversationParticipant.user_id.in_([user1_id, user2_id])
            )
            .group_by(Conversation.id)
            .having(func.count(ConversationParticipant.id) == 2)
        )
        return result.scalar_one_or_none()


class MessageRepository(BaseRepository[Message]):
    def __init__(self):
        super().__init__(Message)

    async def get_by_conversation(
        self,
        db: AsyncSession,
        conversation_id: UUID,
        skip: int = 0,
        limit: int = 50
    ) -> List[Message]:
        result = await db.execute(
            select(Message)
            .where(
                Message.conversation_id == conversation_id,
                Message.is_deleted == False
            )
            .order_by(Message.server_created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def get_recent_by_conversation(
        self,
        db: AsyncSession,
        conversation_id: UUID,
        after_id: Optional[UUID] = None,
        limit: int = 50
    ) -> List[Message]:
        query = select(Message).where(
            Message.conversation_id == conversation_id,
            Message.is_deleted == False
        )
        if after_id:
            query = query.where(Message.id > after_id)

        result = await db.execute(
            query.order_by(Message.server_created_at.desc()).limit(limit)
        )
        return result.scalars().all()

    async def update_status(
        self,
        db: AsyncSession,
        message_id: UUID,
        status: str
    ) -> None:
        now = datetime.now(timezone.utc)
        values = {"status": status}

        if status == MessageStatus.SENT:
            values["sent_at"] = now
        elif status == MessageStatus.DELIVERED:
            values["delivered_at"] = now

        await db.execute(
            update(Message)
            .where(Message.id == message_id)
            .values(**values)
        )
        await db.flush()

    async def mark_as_read(
        self,
        db: AsyncSession,
        conversation_id: UUID,
        user_id: UUID,
        up_to_message_id: UUID
    ) -> int:
        # Mark all messages up to this ID as read by updating conversation participant
        from datetime import datetime, timezone
        result = await db.execute(
            update(ConversationParticipant)
            .where(
                ConversationParticipant.conversation_id == conversation_id,
                ConversationParticipant.user_id == user_id
            )
            .values(last_read_at=datetime.now(timezone.utc))
        )
        return result.rowcount


class ConversationParticipantRepository(BaseRepository[ConversationParticipant]):
    def __init__(self):
        super().__init__(ConversationParticipant)

    async def get_participant(
        self,
        db: AsyncSession,
        conversation_id: UUID,
        user_id: UUID
    ) -> Optional[ConversationParticipant]:
        result = await db.execute(
            select(ConversationParticipant)
            .where(
                ConversationParticipant.conversation_id == conversation_id,
                ConversationParticipant.user_id == user_id,
                ConversationParticipant.left_at.is_(None)
            )
        )
        return result.scalar_one_or_none()

    async def get_other_participants(
        self,
        db: AsyncSession,
        conversation_id: UUID,
        exclude_user_id: UUID
    ) -> List[ConversationParticipant]:
        result = await db.execute(
            select(ConversationParticipant)
            .where(
                ConversationParticipant.conversation_id == conversation_id,
                ConversationParticipant.user_id != exclude_user_id,
                ConversationParticipant.left_at.is_(None)
            )
        )
        return result.scalars().all()


conversation_repo = ConversationRepository()
message_repo = MessageRepository()
participant_repo = ConversationParticipantRepository()
