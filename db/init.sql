-- CodeSync database schema

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS users (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    github_id       BIGINT UNIQUE NOT NULL,
    username        TEXT NOT NULL,
    avatar_url      TEXT,
    access_token    TEXT NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS sessions (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    github_url      TEXT NOT NULL,
    owner           TEXT NOT NULL,
    repo            TEXT NOT NULL,
    ref             TEXT NOT NULL,
    file_path       TEXT NOT NULL,
    language        TEXT,
    created_by      UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_active_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS file_snapshots (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id      UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    content         TEXT NOT NULL,
    sha             TEXT,
    is_original     BOOLEAN NOT NULL DEFAULT false,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_file_snapshots_session ON file_snapshots(session_id, created_at DESC);

CREATE TABLE IF NOT EXISTS comment_threads (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id      UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    line_number     INTEGER NOT NULL,
    resolved        BOOLEAN NOT NULL DEFAULT false,
    resolved_by     UUID REFERENCES users(id) ON DELETE SET NULL,
    resolved_at     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_comment_threads_session ON comment_threads(session_id);

CREATE TABLE IF NOT EXISTS comments (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    thread_id       UUID NOT NULL REFERENCES comment_threads(id) ON DELETE CASCADE,
    user_id         UUID REFERENCES users(id) ON DELETE SET NULL,
    author_name     TEXT NOT NULL,
    body            TEXT NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_comments_thread ON comments(thread_id, created_at);

CREATE TABLE IF NOT EXISTS highlights (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id      UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    user_id         UUID REFERENCES users(id) ON DELETE SET NULL,
    author_name     TEXT NOT NULL,
    start_line      INTEGER NOT NULL,
    end_line        INTEGER NOT NULL,
    color           TEXT NOT NULL DEFAULT '#ffd54f',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_highlights_session ON highlights(session_id);

CREATE TABLE IF NOT EXISTS session_participants (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id      UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    user_id         UUID REFERENCES users(id) ON DELETE SET NULL,
    display_name    TEXT NOT NULL,
    color            TEXT NOT NULL DEFAULT '#42a5f5',
    joined_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_seen_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_participants_session ON session_participants(session_id);
