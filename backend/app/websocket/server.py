import json
import logging
import uuid

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.config import settings
from app.websocket.manager import manager

logger = logging.getLogger("codesync.ws")

router = APIRouter()

# Event types a client is allowed to publish directly (ephemeral, not persisted)
CLIENT_PUBLISHABLE_EVENTS = {"cursor", "presence"}


@router.websocket("/ws/sessions/{session_id}")
async def session_websocket(
    websocket: WebSocket,
    session_id: str,
    client_id: str = Query(default_factory=lambda: str(uuid.uuid4())),
    display_name: str = Query(default="Anonymous"),
    color: str = Query(default="#42a5f5"),
):
    current_count = await manager.participant_count(session_id)
    if current_count >= settings.max_collaborators_per_session:
        await websocket.close(code=4403, reason="Session is at maximum capacity")
        return

    await manager.connect(session_id, client_id, websocket)

    await manager.publish(session_id, {
        "type": "presence_join",
        "client_id": client_id,
        "display_name": display_name,
        "color": color,
    })

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                event = json.loads(raw)
            except json.JSONDecodeError:
                continue

            event_type = event.get("type")
            if event_type not in CLIENT_PUBLISHABLE_EVENTS:
                continue

            event["client_id"] = client_id
            event["display_name"] = display_name
            event["color"] = color
            await manager.publish(session_id, event)
    except WebSocketDisconnect:
        pass
    finally:
        await manager.disconnect(session_id, client_id)
        await manager.publish(session_id, {
            "type": "presence_leave",
            "client_id": client_id,
            "display_name": display_name,
        })
