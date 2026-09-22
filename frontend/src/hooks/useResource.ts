import { useCallback, useEffect, useState } from "react";

export interface UseResourceResult<T> {
  data: T;
  loading: boolean;
  error: string | null;
  refresh: () => void;
}

/** Ce qu'une requête a rendu, et quelle requête c'était. */
interface Reponse<T> {
  fetcher: () => Promise<T>;
  tick: number;
  data: T;
  error: string | null;
}

/**
 * Une donnée distante, lue à chaque changement de `fetcher` — ticket-123.
 *
 * Cinq hooks « fetch + loading + error » quasi identiques coexistaient, et
 * trois d'entre eux n'annulaient pas la réponse en vol au changement de
 * projet : la réponse lente du projet quitté écrasait celle du projet courant.
 *
 * L'identité du `fetcher` **est** la clé de la requête : le passer par
 * `useMemo` sur ses paramètres suffit, et un `fetcher` `null` veut dire
 * « rien à charger ». `loading` et `error` se déduisent en comparant la
 * dernière réponse à la requête courante — aucun `setState` synchrone dans
 * l'effet, donc aucun rendu en cascade.
 *
 * Pendant un `refresh()`, la donnée précédente reste affichée ; au changement
 * de `fetcher`, elle repasse à `initial` — ce qui vient d'un autre projet ne
 * s'affiche pas sous celui-ci.
 */
export function useResource<T>(
  fetcher: (() => Promise<T>) | null,
  initial: T,
): UseResourceResult<T> {
  const [tick, setTick] = useState(0);
  const [reponse, setReponse] = useState<Reponse<T> | null>(null);

  useEffect(() => {
    if (!fetcher) return;
    let cancelled = false;
    fetcher()
      .then((data) => {
        if (cancelled) return;
        setReponse({ fetcher, tick, data, error: null });
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setReponse({
          fetcher,
          tick,
          data: initial,
          error: err instanceof Error ? err.message : "Unknown error",
        });
      });
    return () => {
      cancelled = true;
    };
    // `initial` ne sert qu'en cas d'erreur ; le relire à chaque rendu ne
    // justifie pas de relancer la requête.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fetcher, tick]);

  const refresh = useCallback(() => setTick((t) => t + 1), []);

  const memeRequete = reponse !== null && reponse.fetcher === fetcher;
  const aJour = memeRequete && reponse.tick === tick;

  return {
    data: fetcher !== null && memeRequete ? reponse.data : initial,
    loading: fetcher !== null && !aJour,
    error: aJour ? reponse.error : null,
    refresh,
  };
}
