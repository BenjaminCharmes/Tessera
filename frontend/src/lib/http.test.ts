import { afterEach, describe, expect, it, vi } from "vitest";
import { api } from "./api";
import { request, requestText, send } from "./http";
import { statutsDuRun } from "./statutDuRun";

afterEach(() => {
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
});

type AppelDeFetch = (url: string, init?: RequestInit) => Promise<Response>;

function reponse(corps: string, statut = 200): Response {
  return new Response(corps, { status: statut });
}

describe("send", () => {
  it("prefixes the path with the API root", async () => {
    const fetchSimule = vi.fn<AppelDeFetch>(async () => reponse("{}"));
    vi.stubGlobal("fetch", fetchSimule);

    await send("/projects");

    expect(fetchSimule.mock.calls[0]?.[0]).toBe("/api/v1/projects");
  });

  it("adds the Bearer token when one is set", async () => {
    vi.stubEnv("VITE_STATIC_TOKEN", "secret");
    const fetchSimule = vi.fn<AppelDeFetch>(async () => reponse("{}"));
    vi.stubGlobal("fetch", fetchSimule);

    await send("/projects");

    const init = (fetchSimule.mock.calls[0] as [string, RequestInit | undefined])[1];
    expect(new Headers(init?.headers).get("Authorization")).toBe("Bearer secret");
  });

  it("rejects with the status and the body text on a non-2xx answer", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => reponse("down", 503)));

    await expect(send("/x")).rejects.toThrow("API 503: down");
  });

  it("falls back to the status text when the body cannot be read", async () => {
    const illisible = { ok: false, status: 500, statusText: "Boom", text: () => Promise.reject(new Error("x")) };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(illisible));

    await expect(send("/x")).rejects.toThrow("API 500: Boom");
  });
});

describe("request and requestText", () => {
  it("decodes JSON", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => reponse('{"a":1}')));

    await expect(request<{ a: number }>("/x")).resolves.toEqual({ a: 1 });
  });

  it("reads text", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => reponse("bonjour")));

    await expect(requestText("/x")).resolves.toBe("bonjour");
  });
});

describe("api.git.cleanup", () => {
  it("sends its body as JSON with the matching Content-Type", async () => {
    const fetchSimule = vi.fn<AppelDeFetch>(async () => reponse('["ticket-1"]'));
    vi.stubGlobal("fetch", fetchSimule);

    await api.git.cleanup("ide-core", ["ticket-1"]);

    const [url, init] = fetchSimule.mock.calls[0] as [string, RequestInit | undefined];
    expect(url).toBe("/api/v1/projects/ide-core/branches/cleanup");
    expect(new Headers(init?.headers).get("Content-Type")).toBe("application/json");
    expect(init?.body).toBe(JSON.stringify({ branches: ["ticket-1"] }));
  });
});

describe("statutsDuRun.lire", () => {
  it("reads the stopped tickets of a run", async () => {
    const corps = {
      project_id: "ide-core",
      mode: "queue",
      statut: "arrêté",
      ticket_courant: null,
      approuves: [],
      restants: [],
      debut: "2026-10-24T10:00:00Z",
      fin: null,
      arretes: [{ ticket_id: "ticket-001", motif: "CI rouge" }, { ticket_id: "ticket-002", motif: null }],
    };
    vi.stubGlobal("fetch", vi.fn(async () => reponse(JSON.stringify(corps))));

    const statut = await statutsDuRun.lire("run-1");

    expect(statut.arretes).toEqual(corps.arretes);
  });
});
