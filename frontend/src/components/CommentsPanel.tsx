import { useState } from "react";
import type { CommentThread } from "../types";

interface Props {
  threads: CommentThread[];
  activeLine: number | null;
  authorName: string;
  onCreateThread: (line: number, body: string) => void;
  onReply: (threadId: string, body: string) => void;
  onResolve: (threadId: string) => void;
  onReopen: (threadId: string) => void;
  onJumpToLine: (line: number) => void;
  onCancelNewThread: () => void;
}

export default function CommentsPanel({
  threads,
  activeLine,
  authorName,
  onCreateThread,
  onReply,
  onResolve,
  onReopen,
  onJumpToLine,
  onCancelNewThread,
}: Props) {
  const [newBody, setNewBody] = useState("");
  const [replyBodies, setReplyBodies] = useState<Record<string, string>>({});
  const [showResolved, setShowResolved] = useState(false);

  const sorted = [...threads].sort((a, b) => a.line_number - b.line_number);
  const visible = sorted.filter((t) => showResolved || !t.resolved);

  const submitNew = () => {
    if (!newBody.trim() || activeLine === null) return;
    onCreateThread(activeLine, newBody.trim());
    setNewBody("");
  };

  const submitReply = (threadId: string) => {
    const body = replyBodies[threadId];
    if (!body?.trim()) return;
    onReply(threadId, body.trim());
    setReplyBodies((prev) => ({ ...prev, [threadId]: "" }));
  };

  return (
    <div className="comments-panel">
      <div className="comments-header">
        <h3>Comments</h3>
        <label className="show-resolved-toggle">
          <input type="checkbox" checked={showResolved} onChange={(e) => setShowResolved(e.target.checked)} />
          Show resolved
        </label>
      </div>

      {activeLine !== null && (
        <div className="new-thread-box">
          <div className="new-thread-line">New comment on line {activeLine}</div>
          <textarea
            autoFocus
            value={newBody}
            onChange={(e) => setNewBody(e.target.value)}
            placeholder="Leave a comment..."
          />
          <div className="new-thread-actions">
            <button onClick={submitNew}>Comment</button>
            <button className="secondary" onClick={onCancelNewThread}>
              Cancel
            </button>
          </div>
        </div>
      )}

      <div className="thread-list">
        {visible.length === 0 && <p className="empty-hint">No comments yet. Click a line number to add one.</p>}
        {visible.map((thread) => (
          <div key={thread.id} className={`thread-card ${thread.resolved ? "resolved" : ""}`}>
            <div className="thread-card-header" onClick={() => onJumpToLine(thread.line_number)}>
              <span className="thread-line-badge">Line {thread.line_number}</span>
              {thread.resolved && <span className="resolved-badge">Resolved</span>}
            </div>
            {thread.comments.map((c) => (
              <div key={c.id} className="comment-item">
                <div className="comment-author">{c.author_name}</div>
                <div className="comment-body">{c.body}</div>
              </div>
            ))}
            <div className="thread-actions">
              {!thread.resolved ? (
                <button onClick={() => onResolve(thread.id)}>Resolve</button>
              ) : (
                <button onClick={() => onReopen(thread.id)}>Reopen</button>
              )}
            </div>
            <div className="reply-box">
              <input
                placeholder={`Reply as ${authorName}...`}
                value={replyBodies[thread.id] ?? ""}
                onChange={(e) => setReplyBodies((prev) => ({ ...prev, [thread.id]: e.target.value }))}
                onKeyDown={(e) => {
                  if (e.key === "Enter") submitReply(thread.id);
                }}
              />
              <button onClick={() => submitReply(thread.id)}>Send</button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
