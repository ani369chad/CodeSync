import uuid
from datetime import datetime, timedelta, timezone

from fastapi import Cookie, Depends, HTTPException, status
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models import User

COOKIE_NAME = "codesync_session"


def create_access_token(user_id: uuid.UUID) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> uuid.UUID | None:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        return uuid.UUID(payload["sub"])
    except (JWTError, KeyError, ValueError):
        return None


async def get_optional_user(
    db: AsyncSession,
    codesync_session: str | None,
) -> User | None:
    if not codesync_session:
        return None
    user_id = decode_access_token(codesync_session)
    if not user_id:
        return None
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def get_current_user_optional(
    codesync_session: str | None = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    return await get_optional_user(db, codesync_session)


async def get_current_user_required(
    codesync_session: str | None = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
) -> User:
    user = await get_optional_user(db, codesync_session)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return user
