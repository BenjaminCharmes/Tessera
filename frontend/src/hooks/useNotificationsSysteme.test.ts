import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, renderHook } from "@testing-library/react";
import { useNotificationsSysteme } from "./useNotificationsSysteme";
import { INITIAL, type StreamState } from "./streamState";
import type { RunActif } from "../types/api";

const run: RunActif = {
  run_id: "r1", project_id: "demineur", mode: "single", ticket_id: "ticket-004",
  etape: null, agent: null, tour: 1, tokens_entree: 0, tokens_sortie: 0,
  cout_usd: 0, verdict: null, demarre_a: "2026-09-26T08:00:00Z",
};

const creees: { titre: string; options?: NotificationOptions }[] = [];

class FausseNotification {
  static permission: NotificationPermission = "granted";
  static requestPermission = vi.fn(async () => "granted" as NotificationPermission);
  onclick: (() => void) | null = null;
  constructor(titre: string, options?: NotificationOptions) {
    creees.push({ titre, options });
  }
  close(): void {}
}

function supervision(etat: StreamState, runs: RunActif[] = [run]) {
  return { runs, etatDe: () => etat };
}

describe("useNotificationsSysteme", () => {
  beforeEach(() => {
    creees.length = 0;
    window.localStorage.clear();
    vi.stubGlobal("Notification", FausseNotification);
    Object.defineProperty(document, "visibilityState", { value: "hidden", configurable: true });
  });
  afterEach(() => vi.unstubAllGlobals());

  it("emet une notification quand une question apparait", () => {
    const ouvrir = vi.fn();
    const { rerender } = renderHook(
      ({ etat }: { etat: StreamState }) => useNotificationsSysteme(supervision(etat), "ide-core", ouvrir),
      { initialProps: { etat: { ...INITIAL, status: "running" } } },
    );
    rerender({ etat: { ...INITIAL, status: "running", pendingQuestion: "On casse l'API ?" } });

    expect(creees).toHaveLength(1);
    expect(creees[0].titre).toMatch(/question/);
  });

  it("respecte le reglage coupe, qui survit a un rechargement", () => {
    const premier = renderHook(() => useNotificationsSysteme(supervision({ ...INITIAL, status: "running" }), null, vi.fn()));
    act(() => premier.result.current.setActive(false));
    expect(premier.result.current.etat).toBe("coupees");
    premier.unmount();

    const { result, rerender } = renderHook(
      ({ etat }: { etat: StreamState }) => useNotificationsSysteme(supervision(etat), null, vi.fn()),
      { initialProps: { etat: { ...INITIAL, status: "running" } } },
    );
    expect(result.current.active).toBe(false);
    rerender({ etat: { ...INITIAL, status: "running", pendingQuestion: "?" } });
    expect(creees).toHaveLength(0);
  });

  it("dit quand le navigateur bloque la permission", () => {
    FausseNotification.permission = "denied";
    const { result } = renderHook(() => useNotificationsSysteme(supervision(INITIAL, []), null, vi.fn()));
    expect(result.current.etat).toBe("bloquees");
    FausseNotification.permission = "granted";
  });

  it("ne notifie pas quand la fenetre est visible sur le projet concerne", () => {
    Object.defineProperty(document, "visibilityState", { value: "visible", configurable: true });
    const { rerender } = renderHook(
      ({ etat }: { etat: StreamState }) => useNotificationsSysteme(supervision(etat), "demineur", vi.fn()),
      { initialProps: { etat: { ...INITIAL, status: "running" } } },
    );
    rerender({ etat: { ...INITIAL, status: "running", pendingQuestion: "?" } });
    expect(creees).toHaveLength(0);
  });
});

vi.mock("@tauri-apps/api/core", () => ({ isTauri: vi.fn(() => false) }));
vi.mock("@tauri-apps/plugin-notification", () => ({
  isPermissionGranted: vi.fn(async () => true),
  requestPermission: vi.fn(async () => "granted"),
  sendNotification: vi.fn(),
}));

import { isTauri } from "@tauri-apps/api/core";
import { sendNotification } from "@tauri-apps/plugin-notification";

describe("useNotificationsSysteme — dans l'app desktop (ticket-200)", () => {
  beforeEach(() => {
    creees.length = 0;
    window.localStorage.clear();
    vi.stubGlobal("Notification", FausseNotification);
    Object.defineProperty(document, "visibilityState", { value: "hidden", configurable: true });
    vi.mocked(isTauri).mockReturnValue(true);
    vi.mocked(sendNotification).mockClear();
  });
  afterEach(() => {
    vi.mocked(isTauri).mockReturnValue(false);
    vi.unstubAllGlobals();
  });

  it("passe par le plugin et pas par window.Notification", async () => {
    const { rerender } = renderHook(
      ({ etat }: { etat: StreamState }) => useNotificationsSysteme(supervision(etat), "ide-core", vi.fn()),
      { initialProps: { etat: { ...INITIAL, status: "running" } } },
    );
    rerender({ etat: { ...INITIAL, status: "running", pendingQuestion: "On casse l'API ?" } });

    await vi.waitFor(() => expect(sendNotification).toHaveBeenCalledTimes(1));
    expect(vi.mocked(sendNotification).mock.calls[0][0]).toMatchObject({ body: "On casse l'API ?" });
    expect(creees).toHaveLength(0);
  });
});
