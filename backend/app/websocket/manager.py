import asyncio
import json
import logging
from datetime import datetime, timezone

from fastapi import WebSocket

from app.redis_client import get_redis, session_channel, session_participants_key

logger = logging.getLogger("codesync.ws")


class SessionConnectionManager:
    """Manages local WebSocket connections and relays events through Redis
    pub/sub so that all backend replicas (and all clients within a session)
    receive every real-time event: cursor moves, comments, highlights,
    resolutions.
    """

    def __init__(self) -> None:
        # session_id -> {client_id: WebSocket}
        self._connections: dict[str, dict[str, WebSocket]] = {}
        # session_id -> asyncio.Task subscribing to redis for that session
        self._subscriber_tasks: dict[str, asyncio.Task] = {}
        self._lock = asyncio.Lock()

    async def connect(self, session_id: str, client_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections.setdefault(session_id, {})[client_id] = websocket
            if session_id not in self._subscriber_tasks:
                self._subscriber_tasks[session_id] = asyncio.create_task(
                    self._subscribe_loop(session_id)
                )

        redis_conn = get_redis()
        await redis_conn.hset(
            session_participants_key(session_id),
            client_id,
            json.dumps({"joined_at": datetime.now(timezone.utc).isoformat()}),
        )

    async def disconnect(self, session_id: str, client_id: str) -> None:
        async with self._lock:
            conns = self._connections.get(session_id, {})
            conns.pop(client_id, None)
            if not conns:
                self._connections.pop(session_id, None)
                task = self._subscriber_tasks.pop(session_id, None)
                if task:
                    task.cancel()

        redis_conn = get_redis()
        await redis_conn.hdel(session_participants_key(session_id), client_id)

    async def participant_count(self, session_id: str) -> int:
        redis_conn = get_redis()
        return await redis_conn.hlen(session_participants_key(session_id))

    async def publish(self, session_id: str, event: dict) -> None:
        redis_conn = get_redis()
        await redis_conn.publish(session_channel(session_id), json.dumps(event))

    async def _subscribe_loop(self, session_id: str) -> None:
        redis_conn = get_redis()
        pubsub = redis_conn.pubsub()
        await pubsub.subscribe(session_channel(session_id))
        try:
            async for message in pubsub.listen():
                if message["type"] != "message":
                    continue
                await self._broadcast_local(session_id, message["data"])
        except asyncio.CancelledError:
            pass
        finally:
            await pubsub.unsubscribe(session_channel(session_id))
            await pubsub.aclose()

    async def _broadcast_local(self, session_id: str, raw_data: str) -> None:
        conns = self._connections.get(session_id, {})
        dead_clients = []
        for client_id, ws in conns.items():
            try:
                await ws.send_text(raw_data)
            except Exception:
                dead_clients.append(client_id)
        for client_id in dead_clients:
            conns.pop(client_id, None)


manager = SessionConnectionManager()
