import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Integer, Text, BigInteger, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    github_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    username: Mapped[str] = mapped_column(Text, nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(Text)
    access_token: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    github_url: Mapped[str] = mapped_column(Text, nullable=False)
    owner: Mapped[str] = mapped_column(Text, nullable=False)
    repo: Mapped[str] = mapped_column(Text, nullable=False)
    ref: Mapped[str] = mapped_column(Text, nullable=False)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_active_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    snapshots: Mapped[list["FileSnapshot"]] = relationship(back_populates="session", cascade="all, delete-orphan")
    threads: Mapped[list["CommentThread"]] = relationship(back_populates="session", cascade="all, delete-orphan")
    highlights: Mapped[list["Highlight"]] = relationship(back_populates="session", cascade="all, delete-orphan")


class FileSnapshot(Base):
    __tablename__ = "file_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"))
    content: Mapped[str] = mapped_column(Text, nullable=False)
    sha: Mapped[str | None] = mapped_column(Text)
    is_original: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    session: Mapped["Session"] = relationship(back_populates="snapshots")


class CommentThread(Base):
    __tablename__ = "comment_threads"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"))
    line_number: Mapped[int] = mapped_column(Integer, nullable=False)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    resolved_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    session: Mapped["Session"] = relationship(back_populates="threads")
    comments: Mapped[list["Comment"]] = relationship(back_populates="thread", cascade="all, delete-orphan")


class Comment(Base):
    __tablename__ = "comments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    thread_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("comment_threads.id", ondelete="CASCADE"))
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    author_name: Mapped[str] = mapped_column(Text, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    thread: Mapped["CommentThread"] = relationship(back_populates="comments")


class Highlight(Base):
    __tablename__ = "highlights"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"))
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    author_name: Mapped[str] = mapped_column(Text, nullable=False)
    start_line: Mapped[int] = mapped_column(Integer, nullable=False)
    end_line: Mapped[int] = mapped_column(Integer, nullable=False)
    color: Mapped[str] = mapped_column(Text, default="#ffd54f")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    session: Mapped["Session"] = relationship(back_populates="highlights")


class SessionParticipant(Base):
    __tablename__ = "session_participants"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"))
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    color: Mapped[str] = mapped_column(Text, default="#42a5f5")
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
