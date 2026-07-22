import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth import get_current_user_optional
from app.database import get_db
from app.github_client import fetch_file_content, infer_language, parse_github_url
from app.models import CommentThread, FileSnapshot, Highlight, Session, User
from app.schemas import (
    CreateSessionRequest,
    SaveScratchpadRequest,
    SessionDetailOut,
    SessionOut,
    SnapshotOut,
)
from app.websocket.manager import manager
from app.config import settings

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.post("", response_model=SessionDetailOut, status_code=201)
async def create_session(
    payload: CreateSessionRequest,
    db: AsyncSession = Depends(get_db),
    user: User | None = Depends(get_current_user_optional),
):
    token = user.access_token if user else None
    parsed = await parse_github_url(payload.github_url, token=token)
    content, sha = await fetch_file_content(parsed.owner, parsed.repo, parsed.ref, parsed.path, token=token)

    session = Session(
        github_url=payload.github_url,
        owner=parsed.owner,
        repo=parsed.repo,
        ref=parsed.ref,
        file_path=parsed.path,
        language=infer_language(parsed.path),
        created_by=user.id if user else None,
    )
    db.add(session)
    await db.flush()

    snapshot = FileSnapshot(session_id=session.id, content=content, sha=sha, is_original=True)
    db.add(snapshot)

    await db.commit()
    await db.refresh(session)
    await db.refresh(snapshot)

    return SessionDetailOut(
        session=SessionOut.model_validate(session),
        snapshot=SnapshotOut.model_validate(snapshot),
        threads=[],
        highlights=[],
        participant_count=0,
        max_collaborators=settings.max_collaborators_per_session,
    )


@router.get("/{session_id}", response_model=SessionDetailOut)
async def get_session(session_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    snap_result = await db.execute(
        select(FileSnapshot)
        .where(FileSnapshot.session_id == session_id)
        .order_by(FileSnapshot.created_at.desc())
        .limit(1)
    )
    snapshot = snap_result.scalar_one_or_none()

    threads_result = await db.execute(
        select(CommentThread)
        .where(CommentThread.session_id == session_id)
        .options(selectinload(CommentThread.comments))
        .order_by(CommentThread.line_number)
    )
    threads = threads_result.scalars().all()

    highlights_result = await db.execute(
        select(Highlight).where(Highlight.session_id == session_id).order_by(Highlight.start_line)
    )
    highlights = highlights_result.scalars().all()

    participant_count = await manager.participant_count(str(session_id))

    return SessionDetailOut(
        session=SessionOut.model_validate(session),
        snapshot=SnapshotOut.model_validate(snapshot) if snapshot else None,
        threads=threads,
        highlights=highlights,
        participant_count=participant_count,
        max_collaborators=settings.max_collaborators_per_session,
    )


@router.post("/{session_id}/scratchpad", status_code=204)
async def save_scratchpad(session_id: uuid.UUID, payload: SaveScratchpadRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    snapshot = FileSnapshot(session_id=session_id, content=payload.content, is_original=False)
    db.add(snapshot)
    await db.commit()
    return None
