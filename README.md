# CodeSync

Real-time collaborative code review tool. Paste a GitHub file URL, get a shareable session link, and review code together with live cursors, inline comments, highlights, and a shared scratchpad editor.

## Stack

- **Frontend**: React + TypeScript + Monaco Editor (Vite)
- **Backend**: FastAPI (Python 3.12)
- **CRDT sync**: Yjs + y-websocket (dedicated Node.js server) — powers the collaborative scratchpad editing
- **Pub/sub**: Redis — broadcasts cursor positions, comments, highlights, and thread resolutions to all session participants via a FastAPI WebSocket endpoint
- **Database**: PostgreSQL — persists sessions, file snapshots, comment threads, and highlights
- **Auth**: GitHub OAuth (for accessing private repos)

## Running it

1. Copy `.env.example` to `.env`.
2. [Create a GitHub OAuth App](https://github.com/settings/developers) with callback URL `http://localhost:8000/auth/github/callback`, and fill in `GITHUB_CLIENT_ID` / `GITHUB_CLIENT_SECRET` in `.env`. (Optional — public repos work without logging in.)
3. `docker compose up --build`
4. Open http://localhost:5173

## Architecture notes

- **GitHub URL parsing**: `backend/app/github_client.py` parses any `github.com/.../blob/...` or `raw.githubusercontent.com` URL into owner/repo/ref/path, handling branch names that contain slashes by cross-referencing the repo's branch list.
- **Two real-time channels, deliberately separate**:
  - Yjs/y-websocket (port 1234) handles only the CRDT text sync for the scratchpad — conflict-free concurrent editing.
  - A FastAPI WebSocket (`/ws/sessions/{id}`) backed by Redis pub/sub handles everything that gets persisted: cursor broadcast, new comments, replies, resolutions, and highlights. REST endpoints write to Postgres first, then publish to the session's Redis channel so every connected client (across any number of backend replicas) gets the update immediately.
- **Capacity**: the WebSocket endpoint rejects new connections once a session has 10 active participants (`MAX_COLLABORATORS_PER_SESSION`).
- **Persistence**: the scratchpad content is autosaved to Postgres every 10s from the frontend; the original GitHub fetch is stored as the first (`is_original=true`) snapshot.

## Project structure

```
backend/            FastAPI app, SQLAlchemy models, GitHub client, WebSocket/Redis layer
websocket-server/   Standalone y-websocket (Yjs CRDT) server
frontend/           React + TypeScript + Monaco Editor
db/init.sql          Postgres schema, applied automatically on first container start
docker-compose.yml   Orchestrates all 5 services
```
