import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    username: str
    avatar_url: str | None = None


class CreateSessionRequest(BaseModel):
    github_url: str


class SessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    github_url: str
    owner: str
    repo: str
    ref: str
    file_path: str
    language: str | None
    created_at: datetime


class SnapshotOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    content: str
    sha: str | None
    is_original: bool
    created_at: datetime


class CommentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    thread_id: uuid.UUID
    author_name: str
    body: str
    created_at: datetime


class CommentThreadOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    session_id: uuid.UUID
    line_number: int
    resolved: bool
    resolved_at: datetime | None
    created_at: datetime
    comments: list[CommentOut] = []


class CreateCommentRequest(BaseModel):
    line_number: int
    body: str
    author_name: str


class ReplyCommentRequest(BaseModel):
    body: str
    author_name: str


class HighlightOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    session_id: uuid.UUID
    author_name: str
    start_line: int
    end_line: int
    color: str
    created_at: datetime


class CreateHighlightRequest(BaseModel):
    start_line: int
    end_line: int
    color: str = "#ffd54f"
    author_name: str


class SessionDetailOut(BaseModel):
    session: SessionOut
    snapshot: SnapshotOut | None
    threads: list[CommentThreadOut]
    highlights: list[HighlightOut]
    participant_count: int
    max_collaborators: int


class SaveScratchpadRequest(BaseModel):
    content: str
