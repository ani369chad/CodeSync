import redis.asyncio as redis

from app.config import settings

_redis: redis.Redis | None = None


def get_redis() -> redis.Redis:
    global _redis
    if _redis is None:
        _redis = redis.from_url(settings.redis_url, decode_responses=True)
    return _redis


def session_channel(session_id: str) -> str:
    return f"session:{session_id}:events"


def session_participants_key(session_id: str) -> str:
    return f"session:{session_id}:participants"
