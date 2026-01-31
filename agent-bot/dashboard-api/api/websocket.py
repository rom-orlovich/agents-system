"""WebSocket endpoint for real-time updates."""

import json
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import structlog

from core.database.redis_client import redis_client

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
                    logger.info(
                        "Stop task requested", task_id=task_id, session_id=session_id
                    )
                    # This would be handled by the dashboard API endpoint
                    pass

                elif msg_type == "task.input":
                    # Handle user input to task
                    task_id = message.get("task_id")
                    _user_message = message.get("message")
                    logger.info(
                        "User input received",
                        task_id=task_id,
                        session_id=session_id,
                        has_message=bool(_user_message),
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


@router.websocket("/ws/subagents/{subagent_id}/output")
async def subagent_output_stream(websocket: WebSocket, subagent_id: str):
    """Stream subagent output in real-time."""
    await websocket.accept()

    last_length = 0

    try:
        while True:
            # Get current output
            output = await redis_client.get_subagent_output(subagent_id)
            status = await redis_client.get_subagent_status(subagent_id)

            if output and len(output) > last_length:
                # Send new content
                new_content = output[last_length:]
                await websocket.send_json(
                    {
                        "type": "subagent_output",
                        "subagent_id": subagent_id,
                        "content": new_content,
                        "total_length": len(output),
                    }
                )
                last_length = len(output)

            # Check if subagent is done
            if status and status.get("status") in ["completed", "failed", "stopped"]:
                await websocket.send_json(
                    {
                        "type": "subagent_complete",
                        "subagent_id": subagent_id,
                        "status": status.get("status"),
                    }
                )
                break

            # Poll interval
            await asyncio.sleep(0.5)

    except WebSocketDisconnect:
        logger.info("Subagent stream disconnected", subagent_id=subagent_id)
    except Exception as e:
        logger.error("Subagent stream error", subagent_id=subagent_id, error=str(e))


@router.websocket("/ws/subagents/output")
async def all_subagents_output_stream(websocket: WebSocket):
    """Stream output from all active subagents."""
    await websocket.accept()

    last_lengths = {}

    try:
        while True:
            # Get all active subagents
            active_ids = await redis_client.get_active_subagents()

            for subagent_id in active_ids:
                output = await redis_client.get_subagent_output(subagent_id)
                last_len = last_lengths.get(subagent_id, 0)

                if output and len(output) > last_len:
                    new_content = output[last_len:]
                    await websocket.send_json(
                        {
                            "type": "subagent_output",
                            "subagent_id": subagent_id,
                            "content": new_content,
                        }
                    )
                    last_lengths[subagent_id] = len(output)

            await asyncio.sleep(0.5)

    except WebSocketDisconnect:
        logger.info("All subagents stream disconnected")
    except Exception as e:
        logger.error("All subagents stream error", error=str(e))
