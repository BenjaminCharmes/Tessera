import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
// Every access goes through the backend: the desktop shell has no file
// commands of its own (ticket-124).
import { oublierJeton, saisirJeton } from "./auth";
import { readFile, listEntries } from "./fs";

const mockFetch = vi.fn();
vi.stubGlobal("fetch", mockFetch);

beforeEach(() => {
  mockFetch.mockReset();
});

afterEach(() => {
  oublierJeton();
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

describe("listEntries", () => {
  it("returns the entries with their kind", async () => {
    const entrees = [{ name: "a.md", path: "/some/dir/a.md", is_dir: false }];
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(entrees),
    });
    const result = await listEntries("/some/dir");
    expect(result).toEqual(entrees);
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
    await expect(listEntries("/bad/dir")).rejects.toThrow(
      "Failed to list /bad/dir",
    );
  });
});

// ticket-120 : le mode web de fs.ts parle au même backend que api.ts, avec le
// même 401 si le Bearer manque.
describe("fs et jeton de session (web mode)", () => {
  function authorizationOf(call: number): string | null {
    const [, init] = mockFetch.mock.calls[call] as [string, RequestInit];
    return new Headers(init.headers).get("Authorization");
  }

  it("pose le Bearer sur readFile et listEntries", async () => {
    saisirJeton("s3cret");
    mockFetch.mockResolvedValue({
      ok: true,
      text: () => Promise.resolve(""),
      json: () => Promise.resolve([]),
    });

    await readFile("/a.md");
    await listEntries("/d");

    expect(authorizationOf(0)).toBe("Bearer s3cret");
    expect(authorizationOf(1)).toBe("Bearer s3cret");
  });

  it("n'envoie aucun Authorization sans token", async () => {
    mockFetch.mockResolvedValue({ ok: true, text: () => Promise.resolve("") });

    await readFile("/a.md");

    const [, init] = mockFetch.mock.calls[0] as [string, RequestInit | undefined];
    expect(init).toBeUndefined();
  });
});
