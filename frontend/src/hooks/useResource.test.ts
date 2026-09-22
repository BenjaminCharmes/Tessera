import { describe, it, expect, vi } from "vitest";
import { renderHook, waitFor, act } from "@testing-library/react";
import { useMemo } from "react";
import { useResource } from "./useResource";

/** Une promesse qu'on résout à la main, pour ordonner les réponses. */
function differee<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason: unknown) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

const AUCUN: string[] = [];

function useListe(cle: string | null) {
  const fetcher = useMemo(
    () => (cle ? () => fetchListe(cle) : null),
    [cle],
  );
  return useResource(fetcher, AUCUN);
}

const fetchListe = vi.fn<(cle: string) => Promise<string[]>>();

describe("useResource", () => {
  it("charge au montage puis rend la donnée", async () => {
    fetchListe.mockResolvedValue(["a"]);
    const { result } = renderHook(() => useListe("p1"));

    expect(result.current.loading).toBe(true);
    expect(result.current.data).toBe(AUCUN);

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.data).toEqual(["a"]);
    expect(result.current.error).toBeNull();
  });

  it("reste inerte sans fetcher", () => {
    const { result } = renderHook(() => useListe(null));
    expect(result.current.loading).toBe(false);
    expect(result.current.data).toBe(AUCUN);
    expect(fetchListe).not.toHaveBeenCalled();
  });

  it("ignore la réponse d'un fetcher remplacé pendant le vol (ticket-123)", async () => {
    // `useRuns` et `useUsage` n'annulaient rien : la réponse lente du projet
    // quitté écrasait celle du projet courant, et l'UI mélangeait les deux.
    const lente = differee<string[]>();
    const rapide = differee<string[]>();
    fetchListe.mockImplementationOnce(() => lente.promise);
    fetchListe.mockImplementationOnce(() => rapide.promise);

    const { result, rerender } = renderHook(
      ({ cle }: { cle: string | null }) => useListe(cle),
      { initialProps: { cle: "p1" } as { cle: string | null } },
    );
    act(() => {
      rerender({ cle: "p2" });
    });

    await act(async () => {
      rapide.resolve(["p2"]);
      await rapide.promise;
    });
    await act(async () => {
      lente.resolve(["p1"]);
      await lente.promise;
    });

    expect(result.current.data).toEqual(["p2"]);
    expect(result.current.loading).toBe(false);
  });

  it("refresh() relance le même fetcher et garde la donnée pendant le vol", async () => {
    fetchListe.mockResolvedValue(["a"]);
    const { result } = renderHook(() => useListe("p1"));
    await waitFor(() => expect(result.current.loading).toBe(false));

    fetchListe.mockResolvedValue(["a", "b"]);
    act(() => {
      result.current.refresh();
    });
    expect(result.current.loading).toBe(true);
    expect(result.current.data).toEqual(["a"]);

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.data).toEqual(["a", "b"]);
    expect(fetchListe).toHaveBeenCalledTimes(2);
  });

  it("remonte l'erreur et revient à la valeur initiale", async () => {
    fetchListe.mockRejectedValue(new Error("Network error"));
    const { result } = renderHook(() => useListe("p1"));
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.error).toBe("Network error");
    expect(result.current.data).toBe(AUCUN);
  });

  it("nomme « Unknown error » un rejet qui n'est pas une Error", async () => {
    fetchListe.mockRejectedValue("brut");
    const { result } = renderHook(() => useListe("p1"));
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.error).toBe("Unknown error");
  });

  it("repasse à la valeur initiale quand le fetcher devient null", async () => {
    fetchListe.mockResolvedValue(["a"]);
    const { result, rerender } = renderHook(
      ({ cle }: { cle: string | null }) => useListe(cle),
      { initialProps: { cle: "p1" } as { cle: string | null } },
    );
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.data).toEqual(["a"]);

    act(() => {
      rerender({ cle: null });
    });
    expect(result.current.data).toBe(AUCUN);
    expect(result.current.loading).toBe(false);
  });
});
