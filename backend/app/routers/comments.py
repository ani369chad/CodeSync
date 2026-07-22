import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth import get_current_user_optional
from app.database import get_db
from app.models import Comment, CommentThread, Highlight, Session, User
from app.schemas import (
    CommentOut,
    CommentThreadOut,
    CreateCommentRequest,
    CreateHighlightRequest,
    HighlightOut,
    ReplyCommentRequest,
)
from app.websocket.manager import manager

router = APIRouter(prefix="/api/sessions/{session_id}", tags=["comments"])


async def _get_session_or_404(db: AsyncSession, session_id: uuid.UUID) -> Session:
    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.get("/comments", response_model=list[CommentThreadOut])
async def list_comments(session_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    await _get_session_or_404(db, session_id)
    result = await db.execute(
        select(CommentThread)
        .where(CommentThread.session_id == session_id)
        .options(selectinload(CommentThread.comments))
        .order_by(CommentThread.line_number)
    )
    return result.scalars().all()


@router.post("/comments", response_model=CommentThreadOut, status_code=201)
async def create_comment(
    session_id: uuid.UUID,
    payload: CreateCommentRequest,
    db: AsyncSession = Depends(get_db),
    user: User | None = Depends(get_current_user_optional),
):
    await _get_session_or_404(db, session_id)

    thread = CommentThread(session_id=session_id, line_number=payload.line_number)
    db.add(thread)
    await db.flush()

    comment = Comment(
        thread_id=thread.id,
        user_id=user.id if user else None,
        author_name=payload.author_name,
        body=payload.body,
    )
    db.add(comment)
    await db.commit()
    await db.refresh(thread)
    await db.refresh(comment)

    thread_out = CommentThreadOut(
        id=thread.id,
        session_id=thread.session_id,
        line_number=thread.line_number,
        resolved=thread.resolved,
        resolved_at=thread.resolved_at,
        created_at=thread.created_at,
        comments=[CommentOut.model_validate(comment)],
    )

    await manager.publish(str(session_id), {
        "type": "comment_created",
        "thread": thread_out.model_dump(mode="json"),
    })

    return thread_out


@router.post("/comments/{thread_id}/reply", response_model=CommentOut, status_code=201)
async def reply_comment(
    session_id: uuid.UUID,
    thread_id: uuid.UUID,
    payload: ReplyCommentRequest,
    db: AsyncSession = Depends(get_db),
    user: User | None = Depends(get_current_user_optional),
):
    await _get_session_or_404(db, session_id)
    result = await db.execute(select(CommentThread).where(CommentThread.id == thread_id, CommentThread.session_id == session_id))
    thread = result.scalar_one_or_none()
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    comment = Comment(
        thread_id=thread_id,
        user_id=user.id if user else None,
        author_name=payload.author_name,
        body=payload.body,
    )
    db.add(comment)
    await db.commit()
    await db.refresh(comment)

    comment_out = CommentOut.model_validate(comment)

    await manager.publish(str(session_id), {
        "type": "comment_reply",
        "thread_id": str(thread_id),
        "comment": comment_out.model_dump(mode="json"),
    })

    return comment_out


@router.post("/comments/{thread_id}/resolve", response_model=CommentThreadOut)
async def resolve_thread(
    session_id: uuid.UUID,
    thread_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User | None = Depends(get_current_user_optional),
):
    await _get_session_or_404(db, session_id)
    result = await db.execute(
        select(CommentThread)
        .where(CommentThread.id == thread_id, CommentThread.session_id == session_id)
        .options(selectinload(CommentThread.comments))
    )
    thread = result.scalar_one_or_none()
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    thread.resolved = True
    thread.resolved_by = user.id if user else None
    thread.resolved_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(thread)

    thread_out = CommentThreadOut.model_validate(thread)

    await manager.publish(str(session_id), {
        "type": "thread_resolved",
        "thread_id": str(thread_id),
        "resolved_at": thread.resolved_at.isoformat(),
    })

    return thread_out


@router.post("/comments/{thread_id}/reopen", response_model=CommentThreadOut)
async def reopen_thread(session_id: uuid.UUID, thread_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    await _get_session_or_404(db, session_id)
    result = await db.execute(
        select(CommentThread)
        .where(CommentThread.id == thread_id, CommentThread.session_id == session_id)
        .options(selectinload(CommentThread.comments))
    )
    thread = result.scalar_one_or_none()
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    thread.resolved = False
    thread.resolved_by = None
    thread.resolved_at = None
    await db.commit()
    await db.refresh(thread)

    thread_out = CommentThreadOut.model_validate(thread)

    await manager.publish(str(session_id), {
        "type": "thread_reopened",
        "thread_id": str(thread_id),
    })

    return thread_out


@router.get("/highlights", response_model=list[HighlightOut])
async def list_highlights(session_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    await _get_session_or_404(db, session_id)
    result = await db.execute(select(Highlight).where(Highlight.session_id == session_id).order_by(Highlight.start_line))
    return result.scalars().all()


@router.post("/highlights", response_model=HighlightOut, status_code=201)
async def create_highlight(
    session_id: uuid.UUID,
    payload: CreateHighlightRequest,
    db: AsyncSession = Depends(get_db),
    user: User | None = Depends(get_current_user_optional),
):
    await _get_session_or_404(db, session_id)

    highlight = Highlight(
        session_id=session_id,
        user_id=user.id if user else None,
        author_name=payload.author_name,
        start_line=payload.start_line,
        end_line=payload.end_line,
        color=payload.color,
    )
    db.add(highlight)
    await db.commit()
    await db.refresh(highlight)

    highlight_out = HighlightOut.model_validate(highlight)

    await manager.publish(str(session_id), {
        "type": "highlight_created",
        "highlight": highlight_out.model_dump(mode="json"),
    })

    return highlight_out


@router.delete("/highlights/{highlight_id}", status_code=204)
async def delete_highlight(session_id: uuid.UUID, highlight_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    await _get_session_or_404(db, session_id)
    result = await db.execute(select(Highlight).where(Highlight.id == highlight_id, Highlight.session_id == session_id))
    highlight = result.scalar_one_or_none()
    if not highlight:
        raise HTTPException(status_code=404, detail="Highlight not found")

    await db.delete(highlight)
    await db.commit()

    await manager.publish(str(session_id), {
        "type": "highlight_deleted",
        "highlight_id": str(highlight_id),
    })

    return None
