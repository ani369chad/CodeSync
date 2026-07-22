import type { CommentThread, Highlight, SessionDetail, User } from "../types";

const API_URL = import.meta.env.VITE_API_URL;

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  });

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {
      // ignore
    }
    throw new Error(detail);
  }

  if (res.status === 204) {
    return undefined as T;
  }

  return res.json() as Promise<T>;
}

export const api = {
  me: () => request<User | null>("/auth/me"),
  logout: () => request<{ ok: boolean }>("/auth/logout", { method: "POST" }),
  githubLoginUrl: () => `${API_URL}/auth/github/login`,

  createSession: (github_url: string) =>
    request<SessionDetail>("/api/sessions", {
      method: "POST",
      body: JSON.stringify({ github_url }),
    }),

  getSession: (sessionId: string) => request<SessionDetail>(`/api/sessions/${sessionId}`),

  saveScratchpad: (sessionId: string, content: string) =>
    request<void>(`/api/sessions/${sessionId}/scratchpad`, {
      method: "POST",
      body: JSON.stringify({ content }),
    }),

  listComments: (sessionId: string) => request<CommentThread[]>(`/api/sessions/${sessionId}/comments`),

  createComment: (sessionId: string, line_number: number, body: string, author_name: string) =>
    request<CommentThread>(`/api/sessions/${sessionId}/comments`, {
      method: "POST",
      body: JSON.stringify({ line_number, body, author_name }),
    }),

  replyComment: (sessionId: string, threadId: string, body: string, author_name: string) =>
    request(`/api/sessions/${sessionId}/comments/${threadId}/reply`, {
      method: "POST",
      body: JSON.stringify({ body, author_name }),
    }),

  resolveThread: (sessionId: string, threadId: string) =>
    request<CommentThread>(`/api/sessions/${sessionId}/comments/${threadId}/resolve`, { method: "POST" }),

  reopenThread: (sessionId: string, threadId: string) =>
    request<CommentThread>(`/api/sessions/${sessionId}/comments/${threadId}/reopen`, { method: "POST" }),

  listHighlights: (sessionId: string) => request<Highlight[]>(`/api/sessions/${sessionId}/highlights`),

  createHighlight: (sessionId: string, start_line: number, end_line: number, color: string, author_name: string) =>
    request<Highlight>(`/api/sessions/${sessionId}/highlights`, {
      method: "POST",
      body: JSON.stringify({ start_line, end_line, color, author_name }),
    }),

  deleteHighlight: (sessionId: string, highlightId: string) =>
    request<void>(`/api/sessions/${sessionId}/highlights/${highlightId}`, { method: "DELETE" }),
};
