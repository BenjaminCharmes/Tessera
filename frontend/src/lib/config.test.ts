import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

// Pourquoi ce fichier existe : en release Tauri la page est servie depuis
// `tauri://localhost`, et rien n'y sert `/api/v1`. Le proxy Vite qui résolvait
// les URL relatives en dev n'existe plus : l'origine du backend doit venir de
// la configuration de build, sinon l'app packagée démarre sur une liste de
// projets vide sans dire pourquoi (ticket-124).
//
// `API_ORIGIN` est figée à l'import du module : chaque cas stubbe la variable
// puis recharge `api`, `ws` et `fs` pour lire la valeur qu'il vient de poser.

const mockFetch = vi.fn();

beforeEach(() => {
  vi.resetModules();
  vi.stubGlobal("fetch", mockFetch);
  mockFetch.mockReset();
  mockFetch.mockResolvedValue({
    ok: true,
    json: () => Promise.resolve([]),
    text: () => Promise.resolve(""),
  });
});

afterEach(() => {
  vi.unstubAllEnvs();
});

async function charger() {
  const [{ API_ORIGIN }, { api }, { wsUrl }, { readFile }] = await Promise.all([
    import("./config"),
    import("./api"),
    import("./ws"),
    import("./fs"),
  ]);
  return { API_ORIGIN, api, wsUrl, readFile };
}

describe("sans VITE_API_URL", () => {
  it("garde des URL relatives, résolues par le proxy Vite", async () => {
    vi.stubEnv("VITE_API_URL", undefined);
    const { API_ORIGIN, api, wsUrl } = await charger();

    expect(API_ORIGIN).toBe("");
    await api.projects.list();
    expect(mockFetch).toHaveBeenCalledWith("/api/v1/projects", undefined);
    expect(wsUrl("/api/v1/x")).toBe(`ws://${location.host}/api/v1/x`);
  });
});

describe("avec VITE_API_URL=http://x:1", () => {
  beforeEach(() => {
    vi.stubEnv("VITE_API_URL", "http://x:1");
  });

  it("préfixe les appels REST par l'origine configurée", async () => {
    const { api } = await charger();
    await api.projects.list();
    expect(mockFetch).toHaveBeenCalledWith(
      "http://x:1/api/v1/projects",
      undefined,
    );
  });

  it("ouvre les WebSocket sur l'hôte configuré, pas sur la page", async () => {
    const { wsUrl } = await charger();
    expect(wsUrl("/api/v1/orchestrator/stream/ide-core")).toBe(
      "ws://x:1/api/v1/orchestrator/stream/ide-core",
    );
  });

  it("préfixe aussi les accès fichier, qui passent par le backend", async () => {
    const { readFile } = await charger();
    await readFile("/some/path.md");
    // Sans token, `authorized()` rend `undefined` : le second argument est
    // bien présent, mais vide (ticket-120).
    expect(mockFetch).toHaveBeenCalledWith(
      "http://x:1/api/v1/fs/read?path=%2Fsome%2Fpath.md",
      undefined,
    );
  });
});

describe("la forme de l'origine", () => {
  it("une origine https donne du wss", async () => {
    vi.stubEnv("VITE_API_URL", "https://x:1");
    const { wsUrl } = await charger();
    expect(wsUrl("/api/v1/x")).toBe("wss://x:1/api/v1/x");
  });

  it("un slash final ne produit pas de double slash", async () => {
    vi.stubEnv("VITE_API_URL", "http://x:1/");
    const { api } = await charger();
    await api.projects.list();
    expect(mockFetch).toHaveBeenCalledWith(
      "http://x:1/api/v1/projects",
      undefined,
    );
  });
});
