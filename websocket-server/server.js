import http from "http";
import { WebSocketServer } from "ws";
import { setupWSConnection } from "y-websocket/bin/utils";
import Redis from "ioredis";

const PORT = process.env.PORT || 1234;
const REDIS_URL = process.env.REDIS_URL || "redis://localhost:6379/0";

// Redis is used here to publish lightweight connection-lifecycle metrics so
// the rest of the CodeSync stack (and any future horizontally-scaled
// instance of this server) can observe document activity across the
// cluster. Yjs document state itself is synced peer-to-peer over the
// WebSocket connections in-process, per the y-websocket protocol.
const publisher = new Redis(REDIS_URL);
const subscriber = new Redis(REDIS_URL);

const YJS_ACTIVITY_CHANNEL = "yjs:activity";

subscriber.subscribe(YJS_ACTIVITY_CHANNEL).catch((err) => {
  console.error("Failed to subscribe to Redis channel:", err);
});

const server = http.createServer((req, res) => {
  if (req.url === "/health") {
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ status: "ok" }));
    return;
  }
  res.writeHead(404);
  res.end();
});

const wss = new WebSocketServer({ server });

wss.on("connection", (conn, req) => {
  const url = new URL(req.url, `http://${req.headers.host}`);
  const docName = url.pathname.slice(1) || "default";

  setupWSConnection(conn, req, { docName, gc: true });

  publisher.publish(
    YJS_ACTIVITY_CHANNEL,
    JSON.stringify({ event: "connection_open", doc: docName, at: Date.now() })
  ).catch(() => {});

  conn.on("close", () => {
    publisher.publish(
      YJS_ACTIVITY_CHANNEL,
      JSON.stringify({ event: "connection_close", doc: docName, at: Date.now() })
    ).catch(() => {});
  });
});

server.listen(PORT, () => {
  console.log(`CodeSync Yjs websocket server listening on port ${PORT}`);
});
