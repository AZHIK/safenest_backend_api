import json
import inspect
from typing import Dict, List, Optional, Set
from uuid import UUID

from fastapi import WebSocket, WebSocketDisconnect

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.security import token_manager
from app.repositories.messaging import participant_repo
from app.db.database import get_db

settings = get_settings()
logger = get_logger(__name__)


class ConnectionManager:
    """WebSocket connection manager for real-time messaging and SOS monitoring."""

    def __init__(self):
        # user_id -> list of WebSocket connections (supports multi-device)
        self.active_connections: Dict[str, List[WebSocket]] = {}
        # conversation_id -> set of user_ids
        self.conversation_subscribers: Dict[str, Set[str]] = {}
        # user_id -> set of conversation_ids
        self.user_conversations: Dict[str, Set[str]] = {}

    async def connect(self, websocket: WebSocket, token: str, verify_fns: Optional[List] = None, is_operator: bool = False) -> Optional[str]:
        """Authenticate and connect a WebSocket.
        
        Args:
            websocket: The WebSocket connection
            token: JWT token string
            verify_fns: Optional list of token verification functions.
                       Defaults to [token_manager.verify_access_token] for survivor tokens.
                       Pass [operator_auth_service.verify_access_token] for operator tokens.
            is_operator: Whether this is an operator connection (for auto-subscription)
        """
        try:
            if verify_fns is None:
                verify_fns = [token_manager.verify_access_token]

            payload = None
            for fn in verify_fns:
                result = fn(token)
                if inspect.iscoroutine(result):
                    result = await result
                if result:
                    payload = result
                    break

            if not payload:
                await websocket.close(code=4001, reason="Invalid token")
                return None

            user_id = payload.get("sub")
            if not user_id:
                await websocket.close(code=4001, reason="Invalid token payload")
                return None

            await websocket.accept()
            if user_id not in self.active_connections:
                self.active_connections[user_id] = []
            self.active_connections[user_id].append(websocket)

            logger.info("websocket_connected", user_id=user_id, connections=len(self.active_connections[user_id]), is_operator=is_operator)

            # Auto-subscribe to conversations if operator
            if is_operator:
                await self._auto_subscribe_operator_conversations(user_id)

            return user_id

        except Exception as e:
            logger.error("websocket_connection_error", error=str(e))
            await websocket.close(code=4001, reason="Authentication failed")
            return None

    async def _auto_subscribe_operator_conversations(self, operator_user_id: str):
        """Auto-subscribe operator to all their active conversations."""
        try:
            async with get_db() as db:
                # Get all conversations where this operator is an active participant
                participants = await participant_repo.get_by_operator_user_id(db, UUID(operator_user_id))
                for participant in participants:
                    if participant.left_at is None:
                        self.subscribe_to_conversation(operator_user_id, str(participant.conversation_id))
                logger.info("operator_auto_subscribed", operator_id=operator_user_id, count=len(participants))
        except Exception as e:
            logger.error("operator_auto_subscribe_failed", operator_id=operator_user_id, error=str(e))

    async def disconnect(self, user_id: str, websocket: Optional[WebSocket] = None):
        """Disconnect a WebSocket and clean up."""
        if user_id in self.active_connections:
            if websocket:
                try:
                    self.active_connections[user_id].remove(websocket)
                except ValueError:
                    pass
                if not self.active_connections[user_id]:
                    del self.active_connections[user_id]
            else:
                del self.active_connections[user_id]

        # Remove subscriptions only when ALL connections for this user are gone
        if user_id not in self.active_connections:
            if user_id in self.user_conversations:
                for conv_id in self.user_conversations[user_id]:
                    if conv_id in self.conversation_subscribers:
                        self.conversation_subscribers[conv_id].discard(user_id)
                del self.user_conversations[user_id]

        logger.info("websocket_disconnected", user_id=user_id)

    async def send_personal_message(self, user_id: str, message: dict) -> bool:
        """Send message to a specific user (all their connected devices)."""
        if user_id not in self.active_connections:
            return False

        success = False
        disconnected_conns = []
        for ws in self.active_connections[user_id]:
            try:
                await ws.send_json(message)
                success = True
            except Exception as e:
                logger.error("send_personal_message_failed", user_id=user_id, error=str(e))
                disconnected_conns.append(ws)

        for ws in disconnected_conns:
            await self.disconnect(user_id, ws)

        return success

    async def broadcast(self, message: dict, exclude_user_id: Optional[str] = None):
        """Broadcast to all connected users."""
        disconnected = []

        for user_id, connections in self.active_connections.items():
            if user_id == exclude_user_id:
                continue

            for ws in connections:
                try:
                    await ws.send_json(message)
                except Exception:
                    disconnected.append((user_id, ws))

        # Clean up disconnected clients
        for user_id, ws in disconnected:
            await self.disconnect(user_id, ws)

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

            for ws in self.active_connections[user_id]:
                try:
                    await ws.send_json(message)
                except Exception:
                    disconnected.append((user_id, ws))

        # Clean up disconnected clients
        for user_id, ws in disconnected:
            await self.disconnect(user_id, ws)

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

        await self.broadcast(message)

    def is_connected(self, user_id: str) -> bool:
        """Check if user has any active connections."""
        return user_id in self.active_connections and bool(self.active_connections[user_id])

    def get_connection_count(self) -> int:
        """Get number of active connections."""
        return sum(len(conns) for conns in self.active_connections.values())

    def get_conversation_subscribers(self, conversation_id: str) -> Set[str]:
        """Get set of users subscribed to a conversation."""
        return self.conversation_subscribers.get(conversation_id, set())


# Global instance
connection_manager = ConnectionManager()
