import { withTokenQuery } from "./auth";

export type WsMessage = Record<string, unknown>;

export interface WsOptions {
  onMessage: (data: WsMessage) => void;
  onError?: (event: Event) => void;
  onClose?: (event: CloseEvent) => void;
}

export function createWebSocket(url: string, options: WsOptions): WebSocket {
  const ws = new WebSocket(url);

  ws.onmessage = (event: MessageEvent) => {
    try {
      const data = JSON.parse(event.data as string) as WsMessage;
      options.onMessage(data);
    } catch {
      // ignore malformed frames
    }
  };

  if (options.onError) ws.onerror = options.onError;
  if (options.onClose) ws.onclose = options.onClose;

  return ws;
}

export function wsUrl(path: string): string {
  const proto = location.protocol === "https:" ? "wss:" : "ws:";
  return withTokenQuery(`${proto}//${location.host}${path}`);
}
