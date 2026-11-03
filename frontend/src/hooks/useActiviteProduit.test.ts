import { afterEach, describe, expect, it, vi } from "vitest";
import { act, renderHook, waitFor } from "@testing-library/react";
import { lireActivite } from "../lib/apiActivite";
import { agentsDuService, CADENCE_ACTIVITE_MS, useActiviteProduit } from "./useActiviteProduit";
import type { ActiviteDeService } from "../types/activiteProduit";

vi.mock("../lib/apiActivite", () => ({ lireActivite: vi.fn() }));
const lire = vi.mocked(lireActivite);

afterEach(() => {
  vi.restoreAllMocks();
  vi.useRealTimers();
});

const UNE: ActiviteDeService = {
  project_id: "alpha",
  service: "worker",
  agents: [{ id: "a", nom: "A", etat: "actif", depuis: null, libelle: null }],
};

describe("useActiviteProduit", () => {
  it("reads the activity on mount", async () => {
    lire.mockResolvedValue([UNE]);

    const { result } = renderHook(() => useActiviteProduit());

    expect(result.current).toEqual([]);
    await waitFor(() => expect(result.current).toEqual([UNE]));
  });

  it("reads again every five seconds", async () => {
    vi.useFakeTimers();
    lire.mockResolvedValue([]);

    renderHook(() => useActiviteProduit());
    await act(async () => {});
    expect(lire).toHaveBeenCalledTimes(1);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(CADENCE_ACTIVITE_MS);
    });
    expect(lire).toHaveBeenCalledTimes(2);
    expect(CADENCE_ACTIVITE_MS).toBe(5000);
  });

  it("drops the previous agents when a read fails", async () => {
    vi.useFakeTimers();
    lire.mockResolvedValue([UNE]);
    const { result } = renderHook(() => useActiviteProduit());
    await act(async () => {});
    expect(result.current).toEqual([UNE]);

    lire.mockRejectedValue(new Error("hors ligne"));
    await act(async () => {
      await vi.advanceTimersByTimeAsync(CADENCE_ACTIVITE_MS);
    });

    expect(result.current).toEqual([]);
  });

  it("ignores an answer that is not a list", async () => {
    lire.mockResolvedValue({ detail: "x" } as unknown as ActiviteDeService[]);

    const { result } = renderHook(() => useActiviteProduit());

    await waitFor(() => expect(lire).toHaveBeenCalled());
    expect(result.current).toEqual([]);
  });
});

describe("agentsDuService", () => {
  it("finds the agents of a service, and none for an unknown one", () => {
    expect(agentsDuService([UNE], "alpha", "worker")).toHaveLength(1);
    expect(agentsDuService([UNE], "alpha", "web")).toEqual([]);
    expect(agentsDuService([UNE], "beta", "worker")).toEqual([]);
    expect(agentsDuService([], "alpha", "worker")).toEqual([]);
  });
});
