"""WebSocket endpoint for real-time updates."""

import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import structlog

from shared import ChatMessage, TaskStopMessage, UserInputMessage

logger = structlog.get_logger()

router = APIRouter()


@router.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket connection for real-time updates."""
    ws_hub = websocket.app.state.ws_hub

    await ws_hub.connect(websocket, session_id)

    try:
        while True:
            # Receive messages from client
            data = await websocket.receive_text()

            try:
                message = json.loads(data)
                msg_type = message.get("type")

                if msg_type == "chat.message":
                    # Handle chat message
                    logger.info("Chat message received", session_id=session_id)
                    # This would be handled by the dashboard API endpoint
                    pass

                elif msg_type == "task.stop":
                    # Handle task stop
                    task_id = message.get("task_id")
                    logger.info("Stop task requested", task_id=task_id, session_id=session_id)
                    # This would be handled by the dashboard API endpoint
                    pass

                elif msg_type == "task.input":
                    # Handle user input to task
                    task_id = message.get("task_id")
                    user_message = message.get("message")
                    logger.info(
                        "User input received",
                        task_id=task_id,
                        session_id=session_id
                    )
                    # TODO: Send input to running task
                    pass

            except json.JSONDecodeError:
                logger.warning("Invalid JSON received", session_id=session_id)

    except WebSocketDisconnect:
        ws_hub.disconnect(websocket, session_id)
        logger.info("WebSocket disconnected", session_id=session_id)
    except Exception as e:
        logger.error("WebSocket error", session_id=session_id, error=str(e))
        ws_hub.disconnect(websocket, session_id)
