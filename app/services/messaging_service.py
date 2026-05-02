from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.redis import redis_client
from app.models.messaging import Conversation, ConversationParticipant, Message, MessageStatus
from app.repositories.messaging import (
    conversation_repo,
    message_repo,
    participant_repo,
)
from app.schemas.messaging import (
    ConversationCreate,
    TypingIndicator,
)
from app.websocket.connection_manager import connection_manager


class MessagingService:
    async def create_conversation(
        self,
        db: AsyncSession,
        creator_id: UUID,
        data: ConversationCreate
    ) -> Conversation:
        """Create conversation and return Conversation ORM (with participants eager-loaded)."""
        # Create conversation
        conv_data = {
            "conversation_type": data.conversation_type,
            "title": data.title,
            "created_by": creator_id,
        }
        if data.support_center_id:
            conv_data["support_center_id"] = data.support_center_id

        conversation = await conversation_repo.create(db, conv_data)

        # Add participants
        participants = [creator_id] + data.participant_ids
        for user_id in set(participants):  # Remove duplicates
            participant_data = {
                "conversation_id": conversation.id,
                "user_id": user_id,
                "role": "admin" if user_id == creator_id else "member"
            }
            await participant_repo.create(db, participant_data)

        # Return with eager-loaded participants
        return await conversation_repo.get_by_id_with_participants(db, conversation.id)

    async def get_conversation(
        self,
        db: AsyncSession,
        conversation_id: UUID
    ) -> Conversation:
        """Get conversation and return Conversation ORM (with participants eager-loaded)."""
        conversation = await conversation_repo.get_by_id_with_participants(
            db,
            conversation_id
        )
        if not conversation:
            raise ValueError("Conversation not found")
        return conversation

    async def get_user_conversations(
        self,
        db: AsyncSession,
        user_id: UUID,
        skip: int = 0,
        limit: int = 20
    ) -> List[Conversation]:
        """Get user conversations and return list of Conversation ORMs (with participants eager-loaded)."""
        return await conversation_repo.get_for_user(db, user_id, skip, limit)

    async def send_message(
        self,
        db: AsyncSession,
        sender_id: UUID,
        data
    ) -> Message:
        """Send message and return Message ORM."""
        # Verify sender is participant
        participant = await participant_repo.get_participant(
            db,
            data.conversation_id,
            sender_id
        )
        if not participant:
            raise ValueError("Not a participant in this conversation")

        # Create message
        message_data = {
            "conversation_id": data.conversation_id,
            "sender_id": sender_id,
            "encrypted_content": data.encrypted_content,
            "encryption_metadata": data.encryption_metadata,
            "content_type": data.content_type,
            "reply_to_message_id": data.reply_to_message_id,
            "attachment_encrypted": data.attachment_encrypted,
            "attachment_storage_path": data.attachment_storage_path,
            "attachment_metadata_encrypted": data.attachment_metadata_encrypted,
            "status": MessageStatus.SENT,
            "sent_at": datetime.now(timezone.utc),
            "client_created_at": data.client_created_at,
            "offline_sequence": data.offline_sequence,
        }

        message = await message_repo.create(db, message_data)

        # Update conversation last_message_at
        conversation = await conversation_repo.get_by_id(db, data.conversation_id)
        if conversation:
            conversation.last_message_at = datetime.now(timezone.utc)
            await db.flush()

        # Send real-time notification
        await self._notify_participants(db, data.conversation_id, message, sender_id)

        return message

    async def get_messages(
        self,
        db: AsyncSession,
        conversation_id: UUID,
        user_id: UUID,
        skip: int = 0,
        limit: int = 50
    ) -> List[Message]:
        """Get messages and return list of Message ORMs."""
        # Verify participant
        participant = await participant_repo.get_participant(
            db,
            conversation_id,
            user_id
        )
        if not participant:
            raise ValueError("Not a participant in this conversation")

        return await message_repo.get_by_conversation(db, conversation_id, skip, limit)

    async def mark_conversation_read(
        self,
        db: AsyncSession,
        conversation_id: UUID,
        user_id: UUID
    ) -> bool:
        return await participant_repo.mark_as_read(db, conversation_id, user_id, None) > 0

    async def join_conversation(
        self,
        db: AsyncSession,
        conversation_id: UUID,
        user_id: UUID
    ) -> bool:
        existing = await participant_repo.get_participant(db, conversation_id, user_id)
        if existing:
            return True

        participant_data = {
            "conversation_id": conversation_id,
            "user_id": user_id,
            "role": "member"
        }
        await participant_repo.create(db, participant_data)
        return True

    async def leave_conversation(
        self,
        db: AsyncSession,
        conversation_id: UUID,
        user_id: UUID
    ) -> bool:
        participant = await participant_repo.get_participant(
            db,
            conversation_id,
            user_id
        )
        if participant:
            participant.left_at = datetime.now(timezone.utc)
            await db.flush()
            return True
        return False

    async def send_typing_indicator(
        self,
        conversation_id: UUID,
        user_id: UUID,
        is_typing: bool
    ):
        indicator = TypingIndicator(
            conversation_id=conversation_id,
            user_id=user_id,
            is_typing=is_typing
        )
        await connection_manager.broadcast_to_conversation(
            str(conversation_id),
            {
                "type": "typing",
                "data": indicator.model_dump()
            },
            exclude_user_id=str(user_id)
        )

    async def _notify_participants(
        self,
        db: AsyncSession,
        conversation_id: UUID,
        message: Message,
        sender_id: UUID
    ):
        participants = await participant_repo.get_other_participants(
            db,
            conversation_id,
            sender_id
        )

        notification = {
            "type": "new_message",
            "data": {
                "conversation_id": str(conversation_id),
                "message_id": str(message.id),
                "sender_id": str(sender_id),
                "content_type": message.content_type,
                "sent_at": message.sent_at.isoformat() if message.sent_at else None
            }
        }

        for participant in participants:
            await connection_manager.send_personal_message(
                str(participant.user_id),
                notification
            )


messaging_service = MessagingService()
