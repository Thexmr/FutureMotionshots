import type { StudioEvent } from "@shared/types";

/** Connect to the studio event stream and forward typed events to a handler.
 *  Auto-reconnects with backoff; returns a disposer. */
export function connectStudioSocket(onEvent: (e: StudioEvent) => void): () => void {
  let ws: WebSocket | null = null;
  let closed = false;
  let backoff = 1000;

  const open = () => {
    if (closed) return;
    const proto = location.protocol === "https:" ? "wss" : "ws";
    ws = new WebSocket(`${proto}://${location.host}/ws`);
    ws.onopen = () => (backoff = 1000);
    ws.onmessage = (msg) => {
      try {
        onEvent(JSON.parse(msg.data) as StudioEvent);
      } catch {
        /* ignore malformed frames */
      }
    };
    ws.onclose = () => {
      if (closed) return;
      setTimeout(open, backoff);
      backoff = Math.min(backoff * 2, 15000);
    };
    ws.onerror = () => ws?.close();
  };
  open();

  return () => {
    closed = true;
    ws?.close();
  };
}
