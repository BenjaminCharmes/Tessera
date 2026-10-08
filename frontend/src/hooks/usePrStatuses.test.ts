import { describe, it, expect, vi, afterEach, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { usePrStatuses } from "./usePrStatuses";
import * as apiModule from "../lib/api";
import type { PRStatusEntry } from "../types/api";

function setVisibility(state: "visible" | "hidden"): void {
  Object.defineProperty(document, "visibilityState", {
    value: state,
    configurable: true,
  });
}

beforeEach(() => {
  setVisibility("visible");
});

afterEach(() => {
  setVisibility("visible");
  vi.restoreAllMocks();
});

const settled: PRStatusEntry[] = [
  {
    ticket_id: "ticket-001",
    pr_number: 1,
    state: "merged",
    ci_status: "passing",
    pr_url: "https://github.com/owner/repo/pull/1",
  },
  {
    ticket_id: "ticket-002",
    pr_number: 2,
    state: "closed",
    ci_status: "none",
    pr_url: "https://github.com/owner/repo/pull/2",
  },
];

const withOpen: PRStatusEntry[] = [
  {
    ticket_id: "ticket-003",
    pr_number: 3,
    state: "open",
    ci_status: "pending",
    pr_url: "https://github.com/owner/repo/pull/3",
  },
];

describe("usePrStatuses — toutes les PR réglées", () => {
  it("appelle getPrStatuses une seule fois et ne rappelle pas après 30 s", async () => {
    vi.useFakeTimers();
    try {
      const spy = vi
        .spyOn(apiModule.api.github, "getPrStatuses")
        .mockResolvedValue(settled);

      const { result } = renderHook(() => usePrStatuses("ide-core"));

      // Appel initial + résolution de la promesse + flush React.
      await act(async () => {
        await vi.advanceTimersByTimeAsync(0);
      });
      expect(spy).toHaveBeenCalledTimes(1);

      // Avancer au-delà des 30 s : aucun rappel — les PR sont réglées.
      await act(async () => {
        await vi.advanceTimersByTimeAsync(90_000);
      });
      expect(spy).toHaveBeenCalledTimes(1);

      // La table est bien remplie.
      expect(result.current["ticket-001"]?.state).toBe("merged");
      expect(result.current["ticket-002"]?.state).toBe("closed");
    } finally {
      vi.useRealTimers();
    }
  });
});

describe("usePrStatuses — PR ouverte", () => {
  it("rappelle getPrStatuses après 30 s tant que la PR est ouverte", async () => {
    vi.useFakeTimers();
    try {
      const spy = vi
        .spyOn(apiModule.api.github, "getPrStatuses")
        .mockResolvedValue(withOpen);

      renderHook(() => usePrStatuses("ide-core"));

      // Appel initial.
      await act(async () => {
        await vi.advanceTimersByTimeAsync(0);
      });
      expect(spy).toHaveBeenCalledTimes(1);

      // Un premier rappel après 30 s.
      await act(async () => {
        await vi.advanceTimersByTimeAsync(30_000);
      });
      expect(spy).toHaveBeenCalledTimes(2);
    } finally {
      vi.useRealTimers();
    }
  });

  it("ne rappelle pas pendant que la fenêtre est cachée", async () => {
    vi.useFakeTimers();
    try {
      const spy = vi
        .spyOn(apiModule.api.github, "getPrStatuses")
        .mockResolvedValue(withOpen);

      renderHook(() => usePrStatuses("ide-core"));

      // Appel initial au montage.
      await act(async () => {
        await vi.advanceTimersByTimeAsync(0);
      });
      const apresInit = spy.mock.calls.length;
      expect(apresInit).toBeGreaterThanOrEqual(1);

      // Cacher la fenêtre : l'intervalle doit s'arrêter.
      await act(async () => {
        setVisibility("hidden");
        document.dispatchEvent(new Event("visibilitychange"));
        await vi.advanceTimersByTimeAsync(0);
      });

      // Avancer au-delà de 30 s sans appel supplémentaire.
      await act(async () => {
        await vi.advanceTimersByTimeAsync(90_000);
      });
      expect(spy.mock.calls.length).toBe(apresInit);
    } finally {
      vi.useRealTimers();
    }
  });

  it("reprend le polling quand la fenêtre redevient visible", async () => {
    vi.useFakeTimers();
    try {
      const spy = vi
        .spyOn(apiModule.api.github, "getPrStatuses")
        .mockResolvedValue(withOpen);

      renderHook(() => usePrStatuses("ide-core"));

      await act(async () => {
        await vi.advanceTimersByTimeAsync(0);
      });
      const apresInit = spy.mock.calls.length;

      // Cacher puis réafficher la fenêtre.
      await act(async () => {
        setVisibility("hidden");
        document.dispatchEvent(new Event("visibilitychange"));
        await vi.advanceTimersByTimeAsync(0);
      });
      await act(async () => {
        setVisibility("visible");
        document.dispatchEvent(new Event("visibilitychange"));
        await vi.advanceTimersByTimeAsync(0);
      });

      // Un appel supplémentaire au retour de la fenêtre.
      expect(spy.mock.calls.length).toBeGreaterThan(apresInit);
    } finally {
      vi.useRealTimers();
    }
  });
});

describe("usePrStatuses — projet null", () => {
  it("n'appelle pas getPrStatuses quand projectId est null", async () => {
    vi.useFakeTimers();
    try {
      const spy = vi
        .spyOn(apiModule.api.github, "getPrStatuses")
        .mockResolvedValue([]);

      renderHook(() => usePrStatuses(null));
      await act(async () => {
        await vi.advanceTimersByTimeAsync(90_000);
      });
      expect(spy).not.toHaveBeenCalled();
    } finally {
      vi.useRealTimers();
    }
  });
});
