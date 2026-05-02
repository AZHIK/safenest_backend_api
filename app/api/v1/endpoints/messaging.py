from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.messaging import (
    ConversationCreate,
    ConversationResponse,
    MessageCreate,
    MessageResponse,
    to_conversation_response,
    to_message_response,
)
from app.services.messaging_service import messaging_service
from app.websocket.chat_handler import chat_handler

router = APIRouter()


@router.post("/conversations", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    data: ConversationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new conversation."""
    conversation = await messaging_service.create_conversation(db, current_user.id, data)
    return to_conversation_response(conversation)


@router.get("/conversations", response_model=List[ConversationResponse])
async def get_conversations(
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user's conversations."""
    conversations = await messaging_service.get_user_conversations(
        db,
        current_user.id,
        skip,
        limit
    )
    return [to_conversation_response(c) for c in conversations]


@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get specific conversation."""
    try:
        # First verify membership
        await messaging_service.get_messages(db, conversation_id, current_user.id, limit=1)
        conversation = await messaging_service.get_conversation(db, conversation_id)
        return to_conversation_response(conversation)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.post("/conversations/{conversation_id}/join")
async def join_conversation(
    conversation_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Join a conversation."""
    success = await messaging_service.join_conversation(db, conversation_id, current_user.id)
    if success:
        return {"message": "Joined conversation successfully"}
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Could not join conversation"
    )


@router.post("/conversations/{conversation_id}/leave")
async def leave_conversation(
    conversation_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Leave a conversation."""
    success = await messaging_service.leave_conversation(db, conversation_id, current_user.id)
    if success:
        return {"message": "Left conversation successfully"}
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Could not leave conversation"
    )


@router.get("/conversations/{conversation_id}/messages", response_model=List[MessageResponse])
async def get_messages(
    conversation_id: UUID,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get messages in a conversation."""
    try:
        messages = await messaging_service.get_messages(
            db,
            conversation_id,
            current_user.id,
            skip,
            limit
        )
        return [to_message_response(m) for m in messages]
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.post("/send", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def send_message(
    data: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Send a message to a conversation."""
    try:
        message = await messaging_service.send_message(db, current_user.id, data)
        return to_message_response(message)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/conversations/{conversation_id}/read")
async def mark_read(
    conversation_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Mark all messages in conversation as read."""
    success = await messaging_service.mark_conversation_read(
        db,
        conversation_id,
        current_user.id
    )
    if success:
        return {"message": "Marked as read"}
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Conversation not found"
    )


# WebSocket endpoint for real-time messaging
@router.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket, token: str = None):
    """WebSocket endpoint for real-time chat."""
    if not token:
        await websocket.close(code=4001, reason="Token required")
        return

    await chat_handler.handle_connection(websocket, token)
