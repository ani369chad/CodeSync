import { useEffect, useRef } from "react";
import type { SessionEvent } from "../types";

const WS_URL = import.meta.env.VITE_WS_URL;

export function useSessionSocket(
  sessionId: string,
  clientId: string,
  displayName: string,
  color: string,
  onEvent: (event: SessionEvent) => void
) {
  const wsRef = useRef<WebSocket | null>(null);
  const onEventRef = useRef(onEvent);
  onEventRef.current = onEvent;

  useEffect(() => {
    const params = new URLSearchParams({
      client_id: clientId,
      display_name: displayName,
      color,
    });
    const ws = new WebSocket(`${WS_URL}/ws/sessions/${sessionId}?${params.toString()}`);
    wsRef.current = ws;

    ws.onmessage = (msg) => {
      try {
        const event = JSON.parse(msg.data) as SessionEvent;
        onEventRef.current(event);
      } catch {
        // ignore malformed messages
      }
    };

    return () => {
      ws.close();
      wsRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId, clientId]);

  const sendCursor = (line: number, column: number) => {
    const ws = wsRef.current;
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: "cursor", line, column }));
    }
  };

  return { sendCursor };
}
