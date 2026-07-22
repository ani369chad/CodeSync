export interface User {
  id: string;
  username: string;
  avatar_url: string | null;
}

export interface SessionInfo {
  id: string;
  github_url: string;
  owner: string;
  repo: string;
  ref: string;
  file_path: string;
  language: string | null;
  created_at: string;
}

export interface Snapshot {
  id: string;
  content: string;
  sha: string | null;
  is_original: boolean;
  created_at: string;
}

export interface Comment {
  id: string;
  thread_id: string;
  author_name: string;
  body: string;
  created_at: string;
}

export interface CommentThread {
  id: string;
  session_id: string;
  line_number: number;
  resolved: boolean;
  resolved_at: string | null;
  created_at: string;
  comments: Comment[];
}

export interface Highlight {
  id: string;
  session_id: string;
  author_name: string;
  start_line: number;
  end_line: number;
  color: string;
  created_at: string;
}

export interface SessionDetail {
  session: SessionInfo;
  snapshot: Snapshot | null;
  threads: CommentThread[];
  highlights: Highlight[];
  participant_count: number;
  max_collaborators: number;
}

export interface CursorEvent {
  type: "cursor";
  client_id: string;
  display_name: string;
  color: string;
  line: number;
  column: number;
}

export interface PresenceJoinEvent {
  type: "presence_join";
  client_id: string;
  display_name: string;
  color: string;
}

export interface PresenceLeaveEvent {
  type: "presence_leave";
  client_id: string;
  display_name: string;
}

export interface CommentCreatedEvent {
  type: "comment_created";
  thread: CommentThread;
}

export interface CommentReplyEvent {
  type: "comment_reply";
  thread_id: string;
  comment: Comment;
}

export interface ThreadResolvedEvent {
  type: "thread_resolved";
  thread_id: string;
  resolved_at: string;
}

export interface ThreadReopenedEvent {
  type: "thread_reopened";
  thread_id: string;
}

export interface HighlightCreatedEvent {
  type: "highlight_created";
  highlight: Highlight;
}

export interface HighlightDeletedEvent {
  type: "highlight_deleted";
  highlight_id: string;
}

export type SessionEvent =
  | CursorEvent
  | PresenceJoinEvent
  | PresenceLeaveEvent
  | CommentCreatedEvent
  | CommentReplyEvent
  | ThreadResolvedEvent
  | ThreadReopenedEvent
  | HighlightCreatedEvent
  | HighlightDeletedEvent;
