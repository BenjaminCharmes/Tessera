import { describe, it, expect, vi, afterEach } from "vitest";
import { wsUrl, createWebSocket } from "./ws";

// Minimal WebSocket mock
class MockWebSocket {
  url: string;
  onmessage: ((e: MessageEvent) => void) | null = null;
  onerror: ((e: Event) => void) | null = null;
  onclose: ((e: CloseEvent) => void) | null = null;

  constructor(url: string) {
    this.url = url;
  }
}

vi.stubGlobal("WebSocket", MockWebSocket);

afterEach(() => {
  vi.unstubAllEnvs();
});

describe("wsUrl", () => {
  it("builds ws:// URL from http location", () => {
    const url = wsUrl("/api/v1/foo");
    expect(url).toMatch(/^ws:\/\//);
    expect(url).toMatch(/\/api\/v1\/foo$/);
  });

  it("uses wss:// when protocol is https", () => {
    const proto = location.protocol === "https:" ? "wss:" : "ws:";
    expect(wsUrl("/path")).toBe(`${proto}//${location.host}/path`);
  });

  it("preserves full path including project id", () => {
    const url = wsUrl("/api/v1/orchestrator/stream/ide-core");
    expect(url).toMatch(/\/api\/v1\/orchestrator\/stream\/ide-core$/);
    expect(url).toMatch(/^ws:\/\//);
  });
});

describe("createWebSocket", () => {
  it("returns a WebSocket connected to the given url", () => {
    const ws = createWebSocket("ws://localhost/ws", { onMessage: () => {} });
    expect((ws as unknown as MockWebSocket).url).toBe("ws://localhost/ws");
  });

  it("calls onMessage with parsed JSON on valid message", () => {
    const onMessage = vi.fn();
    const ws = createWebSocket("ws://localhost/ws", { onMessage });
    const mock = ws as unknown as MockWebSocket;
    mock.onmessage!({ data: JSON.stringify({ type: "ping" }) } as MessageEvent);
    expect(onMessage).toHaveBeenCalledWith({ type: "ping" });
  });

  it("ignores malformed JSON without throwing", () => {
    const onMessage = vi.fn();
    const ws = createWebSocket("ws://localhost/ws", { onMessage });
    const mock = ws as unknown as MockWebSocket;
    expect(() => {
      mock.onmessage!({ data: "not json{{" } as MessageEvent);
    }).not.toThrow();
    expect(onMessage).not.toHaveBeenCalled();
  });

  it("wires onerror when provided", () => {
    const onError = vi.fn();
    const ws = createWebSocket("ws://localhost/ws", {
      onMessage: () => {},
      onError,
    });
    const mock = ws as unknown as MockWebSocket;
    mock.onerror!({} as Event);
    expect(onError).toHaveBeenCalled();
  });

  it("leaves onerror null when not provided", () => {
    const ws = createWebSocket("ws://localhost/ws", { onMessage: () => {} });
    const mock = ws as unknown as MockWebSocket;
    expect(mock.onerror).toBeNull();
  });

  it("wires onclose when provided", () => {
    const onClose = vi.fn();
    const ws = createWebSocket("ws://localhost/ws", {
      onMessage: () => {},
      onClose,
    });
    const mock = ws as unknown as MockWebSocket;
    mock.onclose!({} as CloseEvent);
    expect(onClose).toHaveBeenCalled();
  });
});

// ticket-120 : `new WebSocket(url)` n'accepte pas d'en-tête, le token ne peut
// passer que dans l'URL. Le backend ferme en 4401 sinon.
describe("wsUrl et STATIC_TOKEN", () => {
  it("ajoute ?token= quand VITE_STATIC_TOKEN est défini", () => {
    vi.stubEnv("VITE_STATIC_TOKEN", "s3cret");
    expect(wsUrl("/api/v1/agents/stream")).toBe(
      `ws://${location.host}/api/v1/agents/stream?token=s3cret`,
    );
  });

  it("encode le token et enchaîne avec & si la query existe déjà", () => {
    vi.stubEnv("VITE_STATIC_TOKEN", "a b&c");
    expect(wsUrl("/api/v1/x?y=1")).toBe(
      `ws://${location.host}/api/v1/x?y=1&token=a%20b%26c`,
    );
  });

  it("laisse l'URL intacte sans token", () => {
    vi.stubEnv("VITE_STATIC_TOKEN", "");
    expect(wsUrl("/api/v1/agents/stream")).toBe(
      `ws://${location.host}/api/v1/agents/stream`,
    );
  });
});
