import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../api/client";
import CodeEditor, { type RemoteCursor } from "../components/Editor";
import CommentsPanel from "../components/CommentsPanel";
import PresenceBar from "../components/PresenceBar";
import { getDisplayIdentity, useAuth } from "../context/AuthContext";
import { useSessionSocket } from "../hooks/useSessionSocket";
import type { CommentThread, Highlight, SessionDetail, SessionEvent } from "../types";

function randomClientId(): string {
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
}

export default function SessionPage() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const { user, loading: authLoading } = useAuth();

  const [detail, setDetail] = useState<SessionDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [threads, setThreads] = useState<CommentThread[]>([]);
  const [highlights, setHighlights] = useState<Highlight[]>([]);
  const [participants, setParticipants] = useState<Record<string, { name: string; color: string }>>({});
  const [cursors, setCursors] = useState<Record<string, RemoteCursor>>({});
  const [activeLine, setActiveLine] = useState<number | null>(null);
  const [copyState, setCopyState] = useState<"idle" | "copied">("idle");

  const clientIdRef = useRef(randomClientId());
  const getContentRef = useRef<() => string>(() => "");

  const identity = useMemo(() => getDisplayIdentity(user), [user]);

  useEffect(() => {
    if (!sessionId) return;
    api
      .getSession(sessionId)
      .then((d) => {
        setDetail(d);
        setThreads(d.threads);
        setHighlights(d.highlights);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load session"));
  }, [sessionId]);

  const handleEvent = useCallback((event: SessionEvent) => {
    switch (event.type) {
      case "cursor":
        setCursors((prev) => ({
          ...prev,
          [event.client_id]: {
            clientId: event.client_id,
            name: event.display_name,
            color: event.color,
            line: event.line,
            column: event.column,
          },
        }));
        setParticipants((prev) => ({ ...prev, [event.client_id]: { name: event.display_name, color: event.color } }));
        break;
      case "presence_join":
        setParticipants((prev) => ({ ...prev, [event.client_id]: { name: event.display_name, color: event.color } }));
        break;
      case "presence_leave":
        setParticipants((prev) => {
          const next = { ...prev };
          delete next[event.client_id];
          return next;
        });
        setCursors((prev) => {
          const next = { ...prev };
          delete next[event.client_id];
          return next;
        });
        break;
      case "comment_created":
        setThreads((prev) => [...prev, event.thread]);
        break;
      case "comment_reply":
        setThreads((prev) =>
          prev.map((t) => (t.id === event.thread_id ? { ...t, comments: [...t.comments, event.comment] } : t))
        );
        break;
      case "thread_resolved":
        setThreads((prev) =>
          prev.map((t) => (t.id === event.thread_id ? { ...t, resolved: true, resolved_at: event.resolved_at } : t))
        );
        break;
      case "thread_reopened":
        setThreads((prev) =>
          prev.map((t) => (t.id === event.thread_id ? { ...t, resolved: false, resolved_at: null } : t))
        );
        break;
      case "highlight_created":
        setHighlights((prev) => [...prev, event.highlight]);
        break;
      case "highlight_deleted":
        setHighlights((prev) => prev.filter((h) => h.id !== event.highlight_id));
        break;
    }
  }, []);

  const { sendCursor } = useSessionSocket(
    sessionId ?? "",
    clientIdRef.current,
    identity.name,
    identity.color,
    handleEvent
  );

  const lastCursorSentRef = useRef(0);
  const handleCursorMove = useCallback(
    (line: number, column: number) => {
      const now = Date.now();
      if (now - lastCursorSentRef.current < 60) return;
      lastCursorSentRef.current = now;
      sendCursor(line, column);
    },
    [sendCursor]
  );

  // Periodically persist the scratchpad content to Postgres.
  useEffect(() => {
    if (!sessionId) return;
    const interval = setInterval(() => {
      const content = getContentRef.current();
      if (content) {
        api.saveScratchpad(sessionId, content).catch(() => {});
      }
    }, 10000);
    return () => clearInterval(interval);
  }, [sessionId]);

  const handleGutterClick = useCallback((line: number) => {
    setActiveLine((prev) => (prev === line ? null : line));
  }, []);

  const handleCreateThread = useCallback(
    async (line: number, body: string) => {
      if (!sessionId) return;
      await api.createComment(sessionId, line, body, identity.name);
      setActiveLine(null);
    },
    [sessionId, identity.name]
  );

  const handleReply = useCallback(
    async (threadId: string, body: string) => {
      if (!sessionId) return;
      await api.replyComment(sessionId, threadId, body, identity.name);
    },
    [sessionId, identity.name]
  );

  const handleResolve = useCallback(
    async (threadId: string) => {
      if (!sessionId) return;
      await api.resolveThread(sessionId, threadId);
    },
    [sessionId]
  );

  const handleReopen = useCallback(
    async (threadId: string) => {
      if (!sessionId) return;
      await api.reopenThread(sessionId, threadId);
    },
    [sessionId]
  );

  const handleSelectionForHighlight = useCallback(
    async (startLine: number, endLine: number) => {
      if (!sessionId) return;
      await api.createHighlight(sessionId, startLine, endLine, identity.color, identity.name);
    },
    [sessionId, identity.color, identity.name]
  );

  const copyShareLink = () => {
    navigator.clipboard.writeText(window.location.href).then(() => {
      setCopyState("copied");
      setTimeout(() => setCopyState("idle"), 1500);
    });
  };

  if (error) {
    return (
      <div className="centered-page">
        <p className="error-text">{error}</p>
      </div>
    );
  }

  if (!detail || authLoading || !sessionId) {
    return (
      <div className="centered-page">
        <p>Loading session&hellip;</p>
      </div>
    );
  }

  const otherCursors = Object.values(cursors).filter((c) => c.clientId !== clientIdRef.current);
  const otherParticipants = Object.entries(participants)
    .filter(([id]) => id !== clientIdRef.current)
    .map(([clientId, p]) => ({ clientId, ...p }));

  return (
    <div className="session-page">
      <div className="session-topbar">
        <div className="session-file-info">
          <strong>
            {detail.session.owner}/{detail.session.repo}
          </strong>
          <span className="file-path">{detail.session.file_path}</span>
          <span className="ref-badge">{detail.session.ref}</span>
        </div>
        <PresenceBar self={identity} participants={otherParticipants} maxCollaborators={detail.max_collaborators} />
        <button className="share-btn" onClick={copyShareLink}>
          {copyState === "copied" ? "Link copied!" : "Copy share link"}
        </button>
      </div>

      <div className="session-body">
        <div className="editor-pane">
          <div className="editor-hint">Select lines and press Ctrl/Cmd+Shift+H to highlight for everyone.</div>
          <CodeEditor
            sessionId={sessionId}
            language={detail.session.language}
            initialContent={detail.snapshot?.content ?? ""}
            remoteCursors={otherCursors}
            threads={threads}
            highlights={highlights}
            onCursorMove={handleCursorMove}
            onGutterClick={handleGutterClick}
            onSelectionForHighlight={handleSelectionForHighlight}
            onContentSynced={(getContent) => {
              getContentRef.current = getContent;
            }}
          />
        </div>
        <CommentsPanel
          threads={threads}
          activeLine={activeLine}
          authorName={identity.name}
          onCreateThread={handleCreateThread}
          onReply={handleReply}
          onResolve={handleResolve}
          onReopen={handleReopen}
          onJumpToLine={(line) => setActiveLine(line)}
          onCancelNewThread={() => setActiveLine(null)}
        />
      </div>
    </div>
  );
}
