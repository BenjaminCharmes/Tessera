import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
// Every access goes through the backend: the desktop shell has no file
// commands of its own (ticket-124).
import { readFile, writeFile, listDir, listEntries } from "./fs";

const mockFetch = vi.fn();
vi.stubGlobal("fetch", mockFetch);

beforeEach(() => {
  mockFetch.mockReset();
});

afterEach(() => {
  vi.unstubAllEnvs();
});

describe("readFile (web mode)", () => {
  it("returns file content on success", async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      text: () => Promise.resolve("file content"),
    });
    const content = await readFile("/some/path.md");
    expect(content).toBe("file content");
    expect(mockFetch).toHaveBeenCalledWith(
      "/api/v1/fs/read?path=%2Fsome%2Fpath.md",
      undefined,
    );
  });

  it("throws on non-ok response", async () => {
    mockFetch.mockResolvedValue({
      ok: false,
      statusText: "Not Found",
    });
    await expect(readFile("/missing.md")).rejects.toThrow(
      "Failed to read /missing.md",
    );
  });
});

describe("writeFile", () => {
  it("posts content to the write endpoint", async () => {
    mockFetch.mockResolvedValue({ ok: true });
    await writeFile("/some/path.md", "hello");
    expect(mockFetch).toHaveBeenCalledWith(
      "/api/v1/fs/write",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ path: "/some/path.md", content: "hello" }),
      }),
    );
  });

  it("throws on non-ok response", async () => {
    mockFetch.mockResolvedValue({
      ok: false,
      statusText: "Forbidden",
    });
    await expect(writeFile("/locked.md", "data")).rejects.toThrow(
      "Failed to write /locked.md",
    );
  });
});

describe("listDir", () => {
  it("returns list of paths", async () => {
    const files = ["a.md", "b.md"];
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(files),
    });
    const result = await listDir("/some/dir");
    expect(result).toEqual(files);
    expect(mockFetch).toHaveBeenCalledWith(
      "/api/v1/fs/list?path=%2Fsome%2Fdir",
      undefined,
    );
  });

  it("throws on non-ok response", async () => {
    mockFetch.mockResolvedValue({
      ok: false,
      statusText: "Server Error",
    });
    await expect(listDir("/bad/dir")).rejects.toThrow(
      "Failed to list /bad/dir",
    );
  });
});

// ticket-120 : le mode web de fs.ts parle au même backend que api.ts, avec le
// même 401 si le Bearer manque.
describe("fs et STATIC_TOKEN (web mode)", () => {
  function authorizationOf(call: number): string | null {
    const [, init] = mockFetch.mock.calls[call] as [string, RequestInit];
    return new Headers(init.headers).get("Authorization");
  }

  it("pose le Bearer sur readFile, listDir et listEntries", async () => {
    vi.stubEnv("VITE_STATIC_TOKEN", "s3cret");
    mockFetch.mockResolvedValue({
      ok: true,
      text: () => Promise.resolve(""),
      json: () => Promise.resolve([]),
    });

    await readFile("/a.md");
    await listDir("/d");
    await listEntries("/d");

    expect(authorizationOf(0)).toBe("Bearer s3cret");
    expect(authorizationOf(1)).toBe("Bearer s3cret");
    expect(authorizationOf(2)).toBe("Bearer s3cret");
  });

  it("garde Content-Type et le corps sur writeFile", async () => {
    vi.stubEnv("VITE_STATIC_TOKEN", "s3cret");
    mockFetch.mockResolvedValue({ ok: true });

    await writeFile("/a.md", "x");

    const [url, init] = mockFetch.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("/api/v1/fs/write");
    expect(init.method).toBe("POST");
    expect(init.body).toBe(JSON.stringify({ path: "/a.md", content: "x" }));
    const headers = new Headers(init.headers);
    expect(headers.get("Content-Type")).toBe("application/json");
    expect(headers.get("Authorization")).toBe("Bearer s3cret");
  });

  it("n'envoie aucun Authorization sans token", async () => {
    vi.stubEnv("VITE_STATIC_TOKEN", "");
    mockFetch.mockResolvedValue({ ok: true, text: () => Promise.resolve("") });

    await readFile("/a.md");

    const [, init] = mockFetch.mock.calls[0] as [string, RequestInit | undefined];
    expect(init).toBeUndefined();
  });
});
