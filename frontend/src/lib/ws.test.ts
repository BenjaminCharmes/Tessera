import { describe, it, expect, vi } from "vitest";
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
