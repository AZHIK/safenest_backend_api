from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, WebSocket, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.operator_auth import require_operator_permission
from app.operator_services.operator_auth_service import operator_auth_service
from app.models.messaging import Conversation, Message
from app.schemas.messaging import (
    ConversationCreate,
    ConversationResponse,
    MessageCreate,
    MessageResponse,
    to_conversation_response,
    to_message_response,
)
from app.repositories.messaging import conversation_repo, message_repo, participant_repo
from app.services.messaging_service import messaging_service
from app.websocket.chat_handler import chat_handler

router = APIRouter()


@router.post("/conversations", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    data: ConversationCreate,
    current_operator=Depends(require_operator_permission("conversations.manage")),
    db: AsyncSession = Depends(get_db),
):
    """Create a new conversation (admin/operator)."""
    conversation = await messaging_service.create_conversation(
        db, current_operator.id, data, is_operator=True
    )
    return to_conversation_response(conversation)


@router.get("/conversations", response_model=List[ConversationResponse])
async def get_all_conversations(
    skip: int = 0,
    limit: int = 20,
    current_operator=Depends(require_operator_permission("conversations.view")),
    db: AsyncSession = Depends(get_db),
):
    """Get all conversations (admin view)."""
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    result = await db.execute(
        select(Conversation)
        .options(selectinload(Conversation.participants))
        .order_by(Conversation.last_message_at.desc().nullslast())
        .offset(skip)
        .limit(limit)
    )
    conversations = result.scalars().all()
    return [to_conversation_response(c) for c in conversations]


@router.get("/my-conversations", response_model=List[ConversationResponse])
async def get_my_conversations(
    skip: int = 0,
    limit: int = 20,
    current_operator=Depends(require_operator_permission("conversations.view")),
    db: AsyncSession = Depends(get_db),
):
    """Get conversations that the current operator is part of."""
    conversations = await conversation_repo.get_for_operator(db, current_operator.id, skip, limit)
    return [to_conversation_response(c) for c in conversations]


@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: UUID,
    current_operator=Depends(require_operator_permission("conversations.view")),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific conversation by ID."""
    conversation = await conversation_repo.get_by_id_with_participants(db, conversation_id)
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    return to_conversation_response(conversation)


@router.post("/conversations/{conversation_id}/join")
async def join_conversation(
    conversation_id: UUID,
    current_operator=Depends(require_operator_permission("conversations.view")),
    db: AsyncSession = Depends(get_db),
):
    """Join a conversation (operator)."""
    success = await messaging_service.join_conversation(
        db, conversation_id, operator_user_id=current_operator.id
    )
    if success:
        return {"message": "Joined conversation successfully"}
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Could not join conversation"
    )


@router.post("/conversations/{conversation_id}/leave")
async def leave_conversation(
    conversation_id: UUID,
    current_operator=Depends(require_operator_permission("conversations.view")),
    db: AsyncSession = Depends(get_db),
):
    """Leave a conversation (operator)."""
    success = await messaging_service.leave_conversation(
        db, conversation_id, operator_user_id=current_operator.id
    )
    if success:
        return {"message": "Left conversation successfully"}
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Could not leave conversation"
    )


@router.get("/conversations/{conversation_id}/messages", response_model=List[MessageResponse])
async def get_conversation_messages(
    conversation_id: UUID,
    skip: int = 0,
    limit: int = 50,
    current_operator=Depends(require_operator_permission("messages.view")),
    db: AsyncSession = Depends(get_db),
):
    """Get messages in a conversation (admin view)."""
    messages = await messaging_service.get_messages(
        db, conversation_id, operator_user_id=current_operator.id, skip=skip, limit=limit
    )
    return [to_message_response(m) for m in messages]


@router.post("/send", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def send_message(
    data: MessageCreate,
    current_operator=Depends(require_operator_permission("messages.send")),
    db: AsyncSession = Depends(get_db),
):
    """Send a message (operator)."""
    try:
        message = await messaging_service.send_message(
            db, current_operator.id, data, is_operator=True
        )
        return to_message_response(message)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/conversations/{conversation_id}/read")
async def mark_read(
    conversation_id: UUID,
    current_operator=Depends(require_operator_permission("messages.view")),
    db: AsyncSession = Depends(get_db),
):
    """Mark all messages in conversation as read (operator)."""
    success = await messaging_service.mark_conversation_read(
        db, conversation_id, operator_user_id=current_operator.id
    )
    if success:
        return {"message": "Marked as read"}
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Conversation not found"
    )


# WebSocket endpoint for operator real-time messaging
@router.websocket("/ws/chat")
async def operator_websocket_chat(websocket: WebSocket, token: str = None):
    """WebSocket endpoint for operator real-time chat.
    
    Uses operator JWT authentication with domain check and blacklist support.
    """
    if not token:
        await websocket.close(code=4001, reason="Token required")
        return

    await chat_handler.handle_connection(
        websocket, token,
        verify_fns=[operator_auth_service.verify_access_token],
        is_operator=True
    )
