import { afterEach, describe, expect, it, vi } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { useRituels } from "./useRituels";

describe("useRituels interruptions", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("keeps the rituals and returns no interruption when reading them fails", async () => {
    const liste = {
      rituels: [{ id: "r1", statut: "en_retard" }],
      erreur: null,
      synchro: "github",
    };
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string) => {
        if (url.endsWith("/rituels/interruptions")) return new Response("boom", { status: 500 });
        return new Response(JSON.stringify(liste), { status: 200 });
      }),
    );
    const { result } = renderHook(() => useRituels());
    await waitFor(() => expect(result.current.rituels).toHaveLength(1));
    expect(result.current.erreur).toBeNull();
    expect(result.current.interruptions).toEqual([]);
  });
});
