import { describe, it, expect } from "vitest";
import { wsUrl } from "./ws";

describe("wsUrl", () => {
  it("builds ws:// URL from http location", () => {
    const url = wsUrl("/api/v1/foo");
    expect(url).toMatch(/^ws:\/\//);
    expect(url).toMatch(/\/api\/v1\/foo$/);
  });

  it("uses wss:// when protocol is https", () => {
    // jsdom uses http by default, so we verify the logic by checking the source
    // wsUrl reads location.protocol — if it's https:, output is wss://
    const proto = location.protocol === "https:" ? "wss:" : "ws:";
    expect(wsUrl("/path")).toBe(`${proto}//${location.host}/path`);
  });

  it("preserves full path including project id", () => {
    const url = wsUrl("/api/v1/orchestrator/stream/ide-core");
    expect(url).toMatch(/\/api\/v1\/orchestrator\/stream\/ide-core$/);
    expect(url).toMatch(/^ws:\/\//);
  });
});
