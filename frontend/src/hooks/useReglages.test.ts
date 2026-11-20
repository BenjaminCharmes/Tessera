import { describe, expect, it, vi } from "vitest";
import { act, renderHook, waitFor } from "@testing-library/react";
import { useReglages } from "./useReglages";

const api = vi.hoisted(() => ({ list: vi.fn(), ecrire: vi.fn(), retirer: vi.fn() }));

vi.mock("../lib/apiReglages", async () => {
  const reel = await vi.importActual<typeof import("../lib/apiReglages")>("../lib/apiReglages");
  return { ...reel, reglages: api };
});

describe("useReglages", () => {
  it("reloads_after_a_write", async () => {
    api.list.mockResolvedValue([]);
    api.ecrire.mockResolvedValue({});
    const { result } = renderHook(() => useReglages());
    await waitFor(() => expect(result.current.chargement).toBe(false));
    expect(api.list).toHaveBeenCalledTimes(1);
    let retour: string | null = "x";
    await act(async () => {
      retour = await result.current.ecrire("run_max_budget_usd", 9);
    });
    expect(retour).toBeNull();
    expect(api.ecrire).toHaveBeenCalledWith("run_max_budget_usd", 9);
    expect(api.list).toHaveBeenCalledTimes(2);
  });

  it("returns_the_error_text_and_does_not_reload_when_a_write_fails", async () => {
    api.list.mockClear().mockResolvedValue([]);
    api.ecrire.mockRejectedValue(new Error("API 404: introuvable"));
    const { result } = renderHook(() => useReglages());
    await waitFor(() => expect(result.current.chargement).toBe(false));
    let retour: string | null = null;
    await act(async () => {
      retour = await result.current.ecrire("x", 1);
    });
    expect(retour).toBe("Ce réglage n'existe pas.");
    expect(api.list).toHaveBeenCalledTimes(1);
  });
});
