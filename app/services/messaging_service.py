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
from app.repositories.support import support_center_repo
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
        data: ConversationCreate,
        is_operator: bool = False
    ) -> Conversation:
        """Create conversation and return Conversation ORM (with participants eager-loaded).
        If support_center_id is provided and a conversation already exists between
        the creator and that support center, the existing conversation is returned instead.
        """
        # Reuse existing conversation with this support center
        if data.support_center_id and not is_operator:
            existing = await conversation_repo.get_by_support_center_and_user(
                db, data.support_center_id, creator_id
            )
            if existing:
                return existing

        conv_data = {
            "conversation_type": data.conversation_type,
            "title": data.title,
            "created_by": creator_id if not is_operator else None,
        }
        if data.support_center_id:
            conv_data["support_center_id"] = data.support_center_id

        conversation = await conversation_repo.create(db, conv_data)

        # Add creator
        creator_participant_data = {
            "conversation_id": conversation.id,
            "role": "admin"
        }
        if is_operator:
            creator_participant_data["operator_user_id"] = creator_id
        else:
            creator_participant_data["user_id"] = creator_id
        await participant_repo.create(db, creator_participant_data)

        # Add other participants (assuming these are mobile users)
        for user_id in set(data.participant_ids):
            participant_data = {
                "conversation_id": conversation.id,
                "user_id": user_id,
                "role": "member"
            }
            await participant_repo.create(db, participant_data)

        # If conversation is linked to a support center, add its operator(s) as participants
        if data.support_center_id:
            center = await support_center_repo.get_by_id(db, data.support_center_id)
            if center and center.operator_id:
                existing = await participant_repo.get_participant(
                    db, conversation.id, operator_user_id=center.operator_id
                )
                if not existing:
                    operator_participant_data = {
                        "conversation_id": conversation.id,
                        "operator_user_id": center.operator_id,
                        "role": "member"
                    }
                    await participant_repo.create(db, operator_participant_data)

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
        data,
        is_operator: bool = False
    ) -> Message:
        """Send message and return Message ORM."""
        # Verify sender is an active participant (has not left)
        if is_operator:
            participant = await participant_repo.get_active_participant(
                db,
                data.conversation_id,
                operator_user_id=sender_id
            )
        else:
            participant = await participant_repo.get_active_participant(
                db,
                data.conversation_id,
                user_id=sender_id
            )
        if not participant:
            raise ValueError("Not a participant in this conversation")

        # Create message
        message_data = {
            "conversation_id": data.conversation_id,
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
        if is_operator:
            message_data["sender_operator_id"] = sender_id
        else:
            message_data["sender_id"] = sender_id

        message = await message_repo.create(db, message_data)

        # Update conversation last_message_at
        conversation = await conversation_repo.get_by_id(db, data.conversation_id)
        if conversation:
            conversation.last_message_at = datetime.now(timezone.utc)
            await db.flush()

        # Send real-time notification
        await self._notify_participants(db, data.conversation_id, message, sender_id, is_operator)

        return message

    async def get_messages(
        self,
        db: AsyncSession,
        conversation_id: UUID,
        user_id: Optional[UUID] = None,
        operator_user_id: Optional[UUID] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[Message]:
        """Get messages and return list of Message ORMs."""
        # Verify participant
        participant = await participant_repo.get_participant(
            db,
            conversation_id,
            user_id=user_id,
            operator_user_id=operator_user_id
        )
        if not participant:
            raise ValueError("Not a participant in this conversation")

        return await message_repo.get_by_conversation(db, conversation_id, skip, limit)

    async def mark_conversation_read(
        self,
        db: AsyncSession,
        conversation_id: UUID,
        user_id: Optional[UUID] = None,
        operator_user_id: Optional[UUID] = None
    ) -> bool:
        from datetime import datetime, timezone
        participant = await participant_repo.get_participant(
            db,
            conversation_id,
            user_id=user_id,
            operator_user_id=operator_user_id
        )
        if participant:
            participant.last_read_at = datetime.now(timezone.utc)
            await db.flush()
            return True
        return False

    async def join_conversation(
        self,
        db: AsyncSession,
        conversation_id: UUID,
        user_id: Optional[UUID] = None,
        operator_user_id: Optional[UUID] = None
    ) -> bool:
        existing = await participant_repo.get_participant(db, conversation_id, user_id=user_id, operator_user_id=operator_user_id)
        if existing:
            return True

        participant_data = {
            "conversation_id": conversation_id,
            "role": "member"
        }
        if user_id:
            participant_data["user_id"] = user_id
        if operator_user_id:
            participant_data["operator_user_id"] = operator_user_id
        await participant_repo.create(db, participant_data)
        return True

    async def leave_conversation(
        self,
        db: AsyncSession,
        conversation_id: UUID,
        user_id: Optional[UUID] = None,
        operator_user_id: Optional[UUID] = None
    ) -> bool:
        participant = await participant_repo.get_participant(
            db,
            conversation_id,
            user_id=user_id,
            operator_user_id=operator_user_id
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
        sender_id: UUID,
        is_operator: bool
    ):
        if is_operator:
            participants = await participant_repo.get_other_participants(
                db,
                conversation_id,
                exclude_operator_user_id=sender_id
            )
        else:
            participants = await participant_repo.get_other_participants(
                db,
                conversation_id,
                exclude_user_id=sender_id
            )

        notification = {
            "type": "new_message",
            "data": {
                "conversation_id": str(conversation_id),
                "message_id": str(message.id),
                "sender_id": str(sender_id) if not is_operator else None,
                "sender_operator_id": str(sender_id) if is_operator else None,
                "is_operator_sender": is_operator,
                "encrypted_content": message.encrypted_content,
                "encryption_metadata": message.encryption_metadata,
                "content_type": message.content_type,
                "status": message.status,
                "sent_at": message.sent_at.isoformat() if message.sent_at else None,
                "server_created_at": message.server_created_at.isoformat() if message.server_created_at else None
            }
        }

        for participant in participants:
            if participant.user_id:
                await connection_manager.send_personal_message(
                    str(participant.user_id),
                    notification
                )
            if participant.operator_user_id:
                await connection_manager.send_personal_message(
                    str(participant.operator_user_id),
                    notification
                )


messaging_service = MessagingService()
