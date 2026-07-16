import uuid
from datetime import datetime
from enum import Enum
from typing import List, Optional,TYPE_CHECKING

from sqlalchemy import Column, DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .user import User

class ConversationType(str, Enum):
    DIRECT = "direct"
    GROUP = "group"
    SUPPORT = "support"
    ANONYMOUS = "anonymous"


class MessageStatus(str, Enum):
    SENDING = "sending"
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"


class Conversation(SQLModel, table=True):
    __tablename__ = "conversations"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    conversation_type: str = Field(default=ConversationType.DIRECT, max_length=20, index=True)

    # For support conversations
    support_center_id: Optional[uuid.UUID] = Field(default=None, sa_column=Column(ForeignKey("support_centers.id", ondelete="SET NULL")))
    support_ticket_id: Optional[str] = Field(default=None, max_length=50)

    # Metadata
    title: Optional[str] = Field(default=None, max_length=100)  # For group chats
    is_encrypted: bool = Field(default=True)
    encryption_type: str = Field(default="e2ee", max_length=20)  # e2ee, server, none

    # Admin
    created_by: Optional[uuid.UUID] = Field(default=None, sa_column=Column(ForeignKey("users.id", ondelete="SET NULL")))
    created_at: datetime = Field(default=None, sa_column=Column(DateTime(timezone=True), server_default=func.now()))
    updated_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True), onupdate=func.now()))
    last_message_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True), index=True))

    # Archive/Delete
    is_archived: bool = Field(default=False)
    archived_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True)))

    # Relationships
    participants: List["ConversationParticipant"] = Relationship(
        back_populates="conversation",
        sa_relationship_kwargs={"cascade": "all, delete-orphan", "foreign_keys": "ConversationParticipant.conversation_id"}
    )
    messages: List["Message"] = Relationship(
        back_populates="conversation",
        sa_relationship_kwargs={"cascade": "all, delete-orphan", "foreign_keys": "Message.conversation_id"}
    )

    def __repr__(self):
        return f"<Conversation(id={self.id}, type={self.conversation_type})>"


class ConversationParticipant(SQLModel, table=True):
    __tablename__ = "conversation_participants"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    conversation_id: uuid.UUID = Field(sa_column=Column(ForeignKey("conversations.id", ondelete="CASCADE"), index=True))
    user_id: Optional[uuid.UUID] = Field(default=None, sa_column=Column(ForeignKey("users.id", ondelete="CASCADE"), index=True))
    operator_user_id: Optional[uuid.UUID] = Field(default=None, sa_column=Column(ForeignKey("operator_users.id", ondelete="CASCADE"), index=True))

    # Role
    role: str = Field(default="member", max_length=20)  # member, admin, support_agent

    # Notification settings
    notifications_enabled: bool = Field(default=True)
    notifications_muted_until: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True)))

    # E2EE
    public_key: Optional[str] = Field(default=None, sa_column=Column(Text))  # User's public key for this conversation
    key_exchange_complete: bool = Field(default=False)

    # Timestamps
    joined_at: datetime = Field(default=None, sa_column=Column(DateTime(timezone=True), server_default=func.now()))
    left_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True)))
    last_read_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True)))

    # Relationships
    conversation: "Conversation" = Relationship(
        back_populates="participants",
        sa_relationship_kwargs={"foreign_keys": "ConversationParticipant.conversation_id"}
    )
    user: "User" = Relationship(
        back_populates="conversations",
        sa_relationship_kwargs={"foreign_keys": "ConversationParticipant.user_id"}
    )

    # Unique constraints
    __table_args__ = (
        UniqueConstraint('conversation_id', 'user_id', name='unique_conversation_participant'),
        UniqueConstraint('conversation_id', 'operator_user_id', name='unique_conversation_operator_participant'),
    )

    def __repr__(self):
        return f"<ConversationParticipant(conv={self.conversation_id}, user={self.user_id})>"


class Message(SQLModel, table=True):
    __tablename__ = "messages"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    conversation_id: uuid.UUID = Field(sa_column=Column(ForeignKey("conversations.id", ondelete="CASCADE"), index=True))
    sender_id: Optional[uuid.UUID] = Field(default=None, sa_column=Column(ForeignKey("users.id", ondelete="SET NULL"), index=True))
    sender_operator_id: Optional[uuid.UUID] = Field(default=None, sa_column=Column(ForeignKey("operator_users.id", ondelete="SET NULL"), index=True))

    # Reply threading
    reply_to_message_id: Optional[uuid.UUID] = Field(default=None, sa_column=Column(ForeignKey("messages.id", ondelete="SET NULL")))

    # Encrypted content - server only stores and relays
    encrypted_content: str = Field(sa_column=Column(Text))  # Base64 encrypted message
    encryption_metadata: Optional[str] = Field(default=None, sa_column=Column(Text))  # Nonce, key ID, etc.
    content_type: str = Field(default="text", max_length=20)  # text, image, audio, file, location

    # Media attachment reference (encrypted)
    attachment_encrypted: bool = Field(default=False)
    attachment_storage_path: Optional[str] = Field(default=None, sa_column=Column(Text))
    attachment_metadata_encrypted: Optional[str] = Field(default=None, sa_column=Column(Text))

    # Status
    status: str = Field(default=MessageStatus.SENDING, max_length=20, index=True)
    sent_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True)))
    delivered_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True)))

    # Edits and deletion
    is_edited: bool = Field(default=False)
    edited_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True)))
    is_deleted: bool = Field(default=False)
    deleted_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True)))
    deleted_by: Optional[uuid.UUID] = Field(default=None, sa_column=Column(ForeignKey("users.id", ondelete="SET NULL")))

    # Server timestamps
    server_created_at: datetime = Field(default=None, sa_column=Column(DateTime(timezone=True), server_default=func.now()))

    # Client timestamps for offline sync
    client_created_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True)))
    offline_sequence: Optional[int] = Field(default=None)

    # Relationships
    conversation: "Conversation" = Relationship(
        back_populates="messages",
        sa_relationship_kwargs={"foreign_keys": "Message.conversation_id"}
    )
    sender: "User" = Relationship(
        back_populates="sent_messages",
        sa_relationship_kwargs={"foreign_keys": "Message.sender_id"}
    )

    def __repr__(self):
        return f"<Message(id={self.id}, conv={self.conversation_id}, sender={self.sender_id})>"
