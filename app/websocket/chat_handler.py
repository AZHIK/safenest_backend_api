import json
import inspect
from typing import Callable, List, Optional

from fastapi import WebSocket, WebSocketDisconnect

from app.core.logging import get_logger
from app.websocket.connection_manager import connection_manager

logger = get_logger(__name__)


class ChatWebSocketHandler:
    """Handler for chat WebSocket connections."""

    async def handle_connection(self, websocket: WebSocket, token: str, verify_fns: Optional[List[Callable]] = None, is_operator: bool = False):
        """Main WebSocket handler for chat connections.
        
        Args:
            websocket: The WebSocket connection
            token: JWT token string
            verify_fns: Optional list of token verification functions.
                       If None, uses survivor token verification.
            is_operator: Whether this is an operator connection
        """
        user_id = await connection_manager.connect(websocket, token, verify_fns=verify_fns, is_operator=is_operator)
        if not user_id:
            return

        try:
            while True:
                # Receive message
                data = await websocket.receive_text()
                message = json.loads(data)

                # Handle different message types
                await self._handle_message(user_id, message)

        except WebSocketDisconnect:
            await connection_manager.disconnect(user_id, websocket)
        except json.JSONDecodeError:
            await websocket.send_json({
                "type": "error",
                "message": "Invalid JSON format"
            })
        except Exception as e:
            logger.error("websocket_handler_error", user_id=user_id, error=str(e))
            await connection_manager.disconnect(user_id, websocket)

    async def _handle_message(self, user_id: str, message: dict):
        """Route message to appropriate handler."""
        msg_type = message.get("type")

        handlers = {
            "subscribe_conversation": self._handle_subscribe,
            "unsubscribe_conversation": self._handle_unsubscribe,
            "typing": self._handle_typing,
            "ping": self._handle_ping,
            "message_status": self._handle_message_status,
        }

        handler = handlers.get(msg_type)
        if handler:
            await handler(user_id, message.get("data", {}))
        else:
            await self._send_error(user_id, f"Unknown message type: {msg_type}")

    async def _handle_subscribe(self, user_id: str, data: dict):
        """Subscribe to conversation updates."""
        conversation_id = data.get("conversation_id")
        if not conversation_id:
            await self._send_error(user_id, "conversation_id required")
            return

        connection_manager.subscribe_to_conversation(user_id, str(conversation_id))
        await connection_manager.send_personal_message(user_id, {
            "type": "subscribed",
            "conversation_id": conversation_id
        })

    async def _handle_unsubscribe(self, user_id: str, data: dict):
        """Unsubscribe from conversation updates."""
        conversation_id = data.get("conversation_id")
        if conversation_id:
            connection_manager.unsubscribe_from_conversation(user_id, str(conversation_id))

    async def _handle_typing(self, user_id: str, data: dict):
        """Handle typing indicator."""
        conversation_id = data.get("conversation_id")
        is_typing = data.get("is_typing", False)

        if conversation_id:
            await connection_manager.broadcast_to_conversation(
                str(conversation_id),
                {
                    "type": "typing",
                    "user_id": user_id,
                    "conversation_id": str(conversation_id),
                    "is_typing": is_typing
                },
                exclude_user_id=user_id
            )

    async def _handle_ping(self, user_id: str, data: dict):
        """Handle ping/pong keepalive."""
        await connection_manager.send_personal_message(user_id, {
            "type": "pong",
            "timestamp": data.get("timestamp")
        })

    async def _handle_message_status(self, user_id: str, data: dict):
        """Handle message status updates (delivered, read)."""
        conversation_id = data.get("conversation_id")
        message_id = data.get("message_id")
        status = data.get("status")

        if conversation_id and message_id:
            await connection_manager.broadcast_to_conversation(
                str(conversation_id),
                {
                    "type": "message_status",
                    "message_id": message_id,
                    "user_id": user_id,
                    "status": status
                },
                exclude_user_id=user_id
            )

    async def _send_error(self, user_id: str, message: str):
        """Send error message to user."""
        await connection_manager.send_personal_message(user_id, {
            "type": "error",
            "message": message
        })


chat_handler = ChatWebSocketHandler()
