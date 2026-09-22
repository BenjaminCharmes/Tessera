import { withTokenQuery } from "./auth";
import { API_ORIGIN } from "./config";

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

/**
 * URL WebSocket d'un chemin d'API. Sans `VITE_API_URL`, l'hôte est celui de
 * la page (proxy Vite en dev) ; avec, c'est celui du backend configuré —
 * en release Tauri la page vit sur `tauri://localhost`, qui ne sert rien.
 */
export function wsUrl(path: string): string {
  if (API_ORIGIN !== "") {
    const origine = new URL(API_ORIGIN);
    const proto = origine.protocol === "https:" ? "wss:" : "ws:";
    return withTokenQuery(`${proto}//${origine.host}${path}`);
  }
  const proto = location.protocol === "https:" ? "wss:" : "ws:";
  return withTokenQuery(`${proto}//${location.host}${path}`);
}
