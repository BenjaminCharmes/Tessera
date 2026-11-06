import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const invokeSimule = vi.hoisted(() => vi.fn<(commande: string) => Promise<string>>());
vi.mock("@tauri-apps/api/core", () => ({ invoke: invokeSimule }));

type Auth = typeof import("./auth");

// Le fichier de setup charge déjà `auth` avec le vrai `invoke` : on le recharge
// pour que la doublure serve, et pour repartir d'un cache en mémoire vide.
async function charger(): Promise<Auth> {
  vi.resetModules();
  return import("./auth");
}

let auth: Auth;

beforeEach(async () => {
  invokeSimule.mockReset();
  window.history.replaceState(null, "", "/");
  window.sessionStorage.clear();
  auth = await charger();
});

afterEach(() => {
  auth.oublierJeton();
  Reflect.deleteProperty(window, "__TAURI_INTERNALS__");
});

describe("jetonDeSession", () => {
  it("takes the token from the URL fragment, keeps it in sessionStorage and clears the fragment", async () => {
    window.history.replaceState(null, "", "/#jeton=abc");

    await expect(auth.jetonDeSession()).resolves.toBe("abc");

    expect(window.sessionStorage.getItem("tessera.jeton")).toBe("abc");
    expect(window.location.hash).toBe("");
  });

  it("reads sessionStorage before anything else", async () => {
    window.sessionStorage.setItem("tessera.jeton", "stocke");

    await expect(auth.jetonDeSession()).resolves.toBe("stocke");
    expect(invokeSimule).not.toHaveBeenCalled();
  });

  it("calls the Tauri command once for two reads", async () => {
    Object.defineProperty(window, "__TAURI_INTERNALS__", { value: {}, configurable: true });
    invokeSimule.mockResolvedValue("tauri-jeton");

    const premier = await auth.jetonDeSession();
    const second = await auth.jetonDeSession();

    expect([premier, second]).toEqual(["tauri-jeton", "tauri-jeton"]);
    expect(invokeSimule).toHaveBeenCalledTimes(1);
    expect(invokeSimule).toHaveBeenCalledWith("jeton_de_session");
  });

  it("returns an empty token when the Tauri command fails", async () => {
    Object.defineProperty(window, "__TAURI_INTERNALS__", { value: {}, configurable: true });
    invokeSimule.mockRejectedValue("fichier absent");

    await expect(auth.jetonDeSession()).resolves.toBe("");
  });

  it("returns an empty token outside Tauri without a stored one", async () => {
    await expect(auth.jetonDeSession()).resolves.toBe("");
    expect(invokeSimule).not.toHaveBeenCalled();
  });
});

describe("jetonEnCache, saisirJeton and oublierJeton", () => {
  it("serves a typed token, trimmed, then forgets it", () => {
    auth.saisirJeton("  tape  ");

    expect(auth.jetonEnCache()).toBe("tape");
    expect(window.sessionStorage.getItem("tessera.jeton")).toBe("tape");

    auth.oublierJeton();

    expect(auth.jetonEnCache()).toBe("");
  });
});

describe("authorized and withTokenQuery", () => {
  it("leave the request alone without a token", () => {
    const init: RequestInit = { method: "POST" };

    expect(auth.authorized(init)).toBe(init);
    expect(auth.withTokenQuery("ws://h/x")).toBe("ws://h/x");
  });

  it("add the Bearer and the query token when one is set", () => {
    auth.saisirJeton("a b&c");

    const headers = new Headers(auth.authorized({ method: "POST" })?.headers);

    expect(headers.get("Authorization")).toBe("Bearer a b&c");
    expect(auth.withTokenQuery("ws://h/x")).toBe("ws://h/x?token=a%20b%26c");
    expect(auth.withTokenQuery("ws://h/x?y=1")).toBe("ws://h/x?y=1&token=a%20b%26c");
  });
});
