import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor, act } from "@testing-library/react";
import { useMemo } from "react";
import { useResource, _viderCacheResource } from "./useResource";

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

/** Variante avec une `cle` de cache passée à useResource. */
function useListeAvecCle(cle: string | null) {
  const fetcher = useMemo(
    () => (cle ? () => fetchListe(cle) : null),
    [cle],
  );
  return useResource(fetcher, AUCUN, cle ?? undefined);
}

describe("useResource — sans cle (comportement inchangé)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    _viderCacheResource();
  });

  it("sans cle, un changement de fetcher repasse toujours à initial", async () => {
    // Critère ticket-356 : sans cle, le comportement de ticket-123 est intact.
    fetchListe.mockResolvedValueOnce(["p1"]);
    fetchListe.mockResolvedValueOnce(["p2"]);

    const { result, rerender } = renderHook(
      ({ cle }: { cle: string | null }) => useListe(cle),
      { initialProps: { cle: "p1" } as { cle: string | null } },
    );
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.data).toEqual(["p1"]);

    act(() => {
      rerender({ cle: "p2" });
    });

    // Avant que p2 réponde, on doit voir `initial` (pas le cache de p1).
    expect(result.current.data).toBe(AUCUN);
    expect(result.current.loading).toBe(true);

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.data).toEqual(["p2"]);
  });
});

describe("useResource — avec cle (cache ticket-356)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    _viderCacheResource();
  });

  it("rend la donnée en cache aussitôt au retour sur une clé connue, loading vrai", async () => {
    // Critère ticket-356 : revenir sur une clé déjà chargée affiche la donnée
    // précédente immédiatement, avec loading: true le temps du rafraîchissement.
    const lente = differee<string[]>();
    // Séquence : p1 initial → p2 (ignoré) → p1 lent (retour avec cache).
    fetchListe
      .mockResolvedValueOnce(["p1"])
      .mockResolvedValueOnce(["p2-data"])
      .mockImplementationOnce(() => lente.promise);

    // Premier passage sur "p1" : charge et met en cache.
    const { result, rerender } = renderHook(
      ({ cle }: { cle: string | null }) => useListeAvecCle(cle),
      { initialProps: { cle: "p1" } as { cle: string | null } },
    );
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.data).toEqual(["p1"]);

    // Naviguer sur "p2" et attendre son chargement complet.
    act(() => { rerender({ cle: "p2" }); });
    await waitFor(() => expect(result.current.loading).toBe(false));

    // Revenir sur "p1" avec une réponse lente.
    act(() => { rerender({ cle: "p1" }); });

    // La donnée en cache doit être visible immédiatement, et loading doit être vrai.
    expect(result.current.data).toEqual(["p1"]);
    expect(result.current.loading).toBe(true);

    // La réponse arrive : loading passe à false.
    await act(async () => {
      lente.resolve(["p1-rafraichi"]);
      await lente.promise;
    });
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.data).toEqual(["p1-rafraichi"]);
  });
});

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
