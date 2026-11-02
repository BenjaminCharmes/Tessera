import { afterEach, describe, expect, it, vi } from "vitest";
import { act, renderHook, waitFor } from "@testing-library/react";
import { api } from "../lib/api";
import { CADENCE_APPS_MS, useAppsEnCours } from "./useAppsEnCours";
import type { AppEnCours } from "../types/api";

afterEach(() => {
  vi.restoreAllMocks();
  vi.useRealTimers();
});

const UNE: AppEnCours = {
  project_id: "alpha",
  project_name: "Alpha",
  nom: "api",
  origine: "externe",
  pid: 42,
  ports: [8001],
  demarre_a: null,
  memoire_mo: 12,
};

describe("useAppsEnCours", () => {
  it("reads the inventory on mount", async () => {
    vi.spyOn(api.services, "running").mockResolvedValue([UNE]);

    const { result } = renderHook(() => useAppsEnCours());

    expect(result.current.apps).toBeNull();
    await waitFor(() => expect(result.current.apps).toEqual([UNE]));
    expect(result.current.erreur).toBeNull();
  });

  it("reports a read failure", async () => {
    vi.spyOn(api.services, "running").mockRejectedValue(new Error("hors ligne"));

    const { result } = renderHook(() => useAppsEnCours());

    await waitFor(() => expect(result.current.erreur).toBe("hors ligne"));
  });

  it("reads again every ten seconds", async () => {
    vi.useFakeTimers();
    const lire = vi.spyOn(api.services, "running").mockResolvedValue([]);

    renderHook(() => useAppsEnCours());
    await act(async () => {});
    expect(lire).toHaveBeenCalledTimes(1);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(CADENCE_APPS_MS);
    });
    expect(lire).toHaveBeenCalledTimes(2);
  });

  it("ends a launch even when a read is slower than the waiting cadence", async () => {
    vi.useFakeTimers();
    const LANCEE: AppEnCours = { ...UNE, origine: "tessera" };
    let vues: AppEnCours[] = [];
    // La lecture met 3 s, plus que la cadence d'attente (2 s) : chaque tick
    // annulait la lecture en vol, et la réponse n'arrivait jamais.
    vi.spyOn(api.services, "running").mockImplementation(
      () => new Promise((resolve) => setTimeout(() => resolve(vues), 3_000)),
    );
    vi.spyOn(api.services, "start").mockResolvedValue({ services: [] });

    const { result } = renderHook(() => useAppsEnCours());
    await act(async () => {
      await vi.advanceTimersByTimeAsync(3_000);
    });

    vues = [LANCEE];
    await act(async () => {
      await result.current.lancer("alpha");
    });
    expect(result.current.enLancement("alpha")).toBe(true);

    // Seconde par seconde : React rejoue ses effets entre deux `act`, comme entre
    // deux ticks réels ; un seul `act` de 10 s ne verrait aucune annulation.
    for (let s = 0; s < 10; s++) {
      await act(async () => {
        await vi.advanceTimersByTimeAsync(1_000);
      });
    }
    expect(result.current.apps).toEqual([LANCEE]);
    expect(result.current.enLancement("alpha")).toBe(false);
  });

  it("stops an app then reads the inventory again", async () => {
    const lire = vi.spyOn(api.services, "running").mockResolvedValue([UNE]);
    const arreter = vi
      .spyOn(api.services, "stopRunning")
      .mockResolvedValue({ pid: 42, arretes: 1 });

    const { result } = renderHook(() => useAppsEnCours());
    await waitFor(() => expect(result.current.apps).toHaveLength(1));

    lire.mockResolvedValue([]);
    await act(async () => {
      await result.current.arreter(42);
    });

    expect(arreter).toHaveBeenCalledWith(42);
    await waitFor(() => expect(result.current.apps).toEqual([]));
  });

  it("reports a failed stop and keeps the list", async () => {
    vi.spyOn(api.services, "running").mockResolvedValue([UNE]);
    vi.spyOn(api.services, "stopRunning").mockRejectedValue(new Error("API 404"));

    const { result } = renderHook(() => useAppsEnCours());
    await waitFor(() => expect(result.current.apps).toHaveLength(1));

    await act(async () => {
      await result.current.arreter(42);
    });

    expect(result.current.erreur).toBe("API 404");
    expect(result.current.apps).toHaveLength(1);
  });
});
