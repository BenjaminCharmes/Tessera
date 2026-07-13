import { describe, it, expect, vi, beforeEach } from "vitest";
// jsdom has no __TAURI_INTERNALS__ by default → isTauri is false → web mode
import { readFile, writeFile, listDir } from "./fs";

const mockFetch = vi.fn();
vi.stubGlobal("fetch", mockFetch);

beforeEach(() => {
  mockFetch.mockReset();
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

describe("writeFile (web mode)", () => {
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

describe("listDir (web mode)", () => {
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
