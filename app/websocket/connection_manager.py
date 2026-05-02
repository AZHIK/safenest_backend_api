import json
from typing import Dict, List, Optional, Set
from uuid import UUID

from fastapi import WebSocket, WebSocketDisconnect

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.security import token_manager

settings = get_settings()
logger = get_logger(__name__)


class ConnectionManager:
    """WebSocket connection manager for real-time messaging and SOS monitoring."""

    def __init__(self):
        # user_id -> WebSocket
        self.active_connections: Dict[str, WebSocket] = {}
        # conversation_id -> set of user_ids
        self.conversation_subscribers: Dict[str, Set[str]] = {}
        # user_id -> set of conversation_ids
        self.user_conversations: Dict[str, Set[str]] = {}

    async def connect(self, websocket: WebSocket, token: str) -> Optional[str]:
        """Authenticate and connect a WebSocket."""
        try:
            payload = token_manager.verify_access_token(token)
            if not payload:
                await websocket.close(code=4001, reason="Invalid token")
                return None

            user_id = payload.get("sub")
            if not user_id:
                await websocket.close(code=4001, reason="Invalid token payload")
                return None

            await websocket.accept()
            self.active_connections[user_id] = websocket

            logger.info("websocket_connected", user_id=user_id)
            return user_id

        except Exception as e:
            logger.error("websocket_connection_error", error=str(e))
            await websocket.close(code=4001, reason="Authentication failed")
            return None

    async def disconnect(self, user_id: str):
        """Disconnect and clean up."""
        if user_id in self.active_connections:
            del self.active_connections[user_id]

        # Remove from all conversations
        if user_id in self.user_conversations:
            for conv_id in self.user_conversations[user_id]:
                if conv_id in self.conversation_subscribers:
                    self.conversation_subscribers[conv_id].discard(user_id)
            del self.user_conversations[user_id]

        logger.info("websocket_disconnected", user_id=user_id)

    async def send_personal_message(self, user_id: str, message: dict) -> bool:
        """Send message to a specific user."""
        if user_id not in self.active_connections:
            return False

        try:
            websocket = self.active_connections[user_id]
            await websocket.send_json(message)
            return True
        except Exception as e:
            logger.error("send_personal_message_failed", user_id=user_id, error=str(e))
            return False

    async def broadcast(self, message: dict, exclude_user_id: Optional[str] = None):
        """Broadcast to all connected users."""
        disconnected = []

        for user_id, websocket in self.active_connections.items():
            if user_id == exclude_user_id:
                continue

            try:
                await websocket.send_json(message)
            except Exception:
                disconnected.append(user_id)

        # Clean up disconnected clients
        for user_id in disconnected:
            await self.disconnect(user_id)

    def subscribe_to_conversation(self, user_id: str, conversation_id: str):
        """Subscribe user to conversation updates."""
        if conversation_id not in self.conversation_subscribers:
            self.conversation_subscribers[conversation_id] = set()
        self.conversation_subscribers[conversation_id].add(user_id)

        if user_id not in self.user_conversations:
            self.user_conversations[user_id] = set()
        self.user_conversations[user_id].add(conversation_id)

        logger.debug(
            "conversation_subscribed",
            user_id=user_id,
            conversation_id=conversation_id
        )

    def unsubscribe_from_conversation(self, user_id: str, conversation_id: str):
        """Unsubscribe user from conversation updates."""
        if conversation_id in self.conversation_subscribers:
            self.conversation_subscribers[conversation_id].discard(user_id)

        if user_id in self.user_conversations:
            self.user_conversations[user_id].discard(conversation_id)

    async def broadcast_to_conversation(
        self,
        conversation_id: str,
        message: dict,
        exclude_user_id: Optional[str] = None
    ):
        """Send message to all participants in a conversation."""
        if conversation_id not in self.conversation_subscribers:
            return

        disconnected = []
        subscribers = self.conversation_subscribers[conversation_id].copy()

        for user_id in subscribers:
            if user_id == exclude_user_id:
                continue

            if user_id not in self.active_connections:
                continue

            try:
                websocket = self.active_connections[user_id]
                await websocket.send_json(message)
            except Exception:
                disconnected.append(user_id)

        # Clean up disconnected clients
        for user_id in disconnected:
            await self.disconnect(user_id)

    async def handle_sos_update(self, alert_id: str, update_data: dict):
        """Broadcast SOS alert updates to relevant parties."""
        message = {
            "type": "sos_update",
            "alert_id": alert_id,
            "data": update_data
        }

        # Notify alert creator
        user_id = update_data.get("user_id")
        if user_id:
            await self.send_personal_message(user_id, message)

    async def handle_location_update(self, alert_id: str, location_data: dict):
        """Broadcast real-time location updates."""
        message = {
            "type": "location_update",
            "alert_id": alert_id,
            "location": location_data
        }

        # Notify all connected parties monitoring this alert
        # This would be extended based on your specific requirements
        await self.broadcast(message)

    def is_connected(self, user_id: str) -> bool:
        """Check if user is currently connected."""
        return user_id in self.active_connections

    def get_connection_count(self) -> int:
        """Get number of active connections."""
        return len(self.active_connections)

    def get_conversation_subscribers(self, conversation_id: str) -> Set[str]:
        """Get set of users subscribed to a conversation."""
        return self.conversation_subscribers.get(conversation_id, set())


# Global instance
connection_manager = ConnectionManager()
