from datetime import datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ConversationCreate(BaseModel):
    conversation_type: str = Field(default="direct", pattern=r"^(direct|group|support|anonymous)$")
    participant_ids: List[UUID] = Field(default_factory=list, max_length=50)
    title: Optional[str] = Field(default=None, max_length=100)
    support_center_id: Optional[UUID] = None


class ConversationParticipantResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: Optional[UUID]
    operator_user_id: Optional[UUID]
    role: str
    joined_at: datetime
    last_read_at: Optional[datetime]


class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    conversation_type: str
    title: Optional[str]
    is_encrypted: bool
    encryption_type: str
    last_message_at: Optional[datetime]
    created_at: datetime
    participants: List[ConversationParticipantResponse] = []


class MessageCreate(BaseModel):
    conversation_id: UUID
    encrypted_content: str = Field(..., min_length=1)
    encryption_metadata: str = Field(...)
    content_type: str = Field(default="text", pattern=r"^(text|image|audio|file|location)$")
    reply_to_message_id: Optional[UUID] = None

    # Optional attachment
    attachment_encrypted: bool = False
    attachment_storage_path: Optional[str] = None
    attachment_metadata_encrypted: Optional[str] = None

    # Offline support
    client_created_at: datetime
    offline_sequence: Optional[int] = None


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    conversation_id: UUID
    sender_id: Optional[UUID]
    sender_operator_id: Optional[UUID]
    encrypted_content: str
    encryption_metadata: str
    content_type: str
    status: str
    sent_at: Optional[datetime]
    delivered_at: Optional[datetime]
    is_edited: bool
    is_deleted: bool
    server_created_at: datetime
    client_created_at: Optional[datetime]


class MessageDeliveryReceipt(BaseModel):
    message_id: UUID
    delivered_at: datetime


class MessageReadReceipt(BaseModel):
    message_id: UUID
    read_at: datetime


class TypingIndicator(BaseModel):
    conversation_id: UUID
    user_id: UUID
    is_typing: bool


# Mapper functions for safe ORM -> Schema conversion
# These must be called ONLY after all relationships are eagerly loaded

def to_conversation_participant_response(participant) -> ConversationParticipantResponse:
    """Convert ConversationParticipant ORM to response schema."""
    return ConversationParticipantResponse(
        id=participant.id,
        user_id=participant.user_id,
        operator_user_id=participant.operator_user_id,
        role=participant.role,
        joined_at=participant.joined_at,
        last_read_at=participant.last_read_at
    )


def to_conversation_response(conversation) -> ConversationResponse:
    """Convert Conversation ORM to response schema. Must be called after participants eager-loaded."""
    return ConversationResponse(
        id=conversation.id,
        conversation_type=conversation.conversation_type,
        title=conversation.title,
        is_encrypted=conversation.is_encrypted,
        encryption_type=conversation.encryption_type,
        last_message_at=conversation.last_message_at,
        created_at=conversation.created_at,
        participants=[
            to_conversation_participant_response(p)
            for p in (getattr(conversation, 'participants', None) or [])
        ]
    )


def to_message_response(message) -> MessageResponse:
    """Convert Message ORM to response schema."""
    return MessageResponse(
        id=message.id,
        conversation_id=message.conversation_id,
        sender_id=message.sender_id,
        sender_operator_id=message.sender_operator_id,
        encrypted_content=message.encrypted_content,
        encryption_metadata=message.encryption_metadata,
        content_type=message.content_type,
        status=message.status,
        sent_at=message.sent_at,
        delivered_at=message.delivered_at,
        is_edited=message.is_edited,
        is_deleted=message.is_deleted,
        server_created_at=message.server_created_at,
        client_created_at=message.client_created_at
    )
