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

// Cache de niveau module — borné à 100 entrées, LRU (ticket-356).
// La Map préserve l'ordre d'insertion : `keys().next()` donne la plus ancienne.
const _cache = new Map<string, unknown>();
const CACHE_MAX = 100;

function getCached<T>(cle: string): T | undefined {
  return _cache.get(cle) as T | undefined;
}

function setCached(cle: string, value: unknown): void {
  // Supprimer pour réinsérer en fin : la Map garde l'ordre, LRU naturel.
  _cache.delete(cle);
  if (_cache.size >= CACHE_MAX) {
    const oldest = _cache.keys().next().value as string | undefined;
    if (oldest !== undefined) _cache.delete(oldest);
  }
  _cache.set(cle, value);
}

/** Vide le cache — pour les tests uniquement. */
export function _viderCacheResource(): void {
  _cache.clear();
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
 *
 * Avec une `cle` (ticket-356), la dernière donnée obtenue pour cette clé est
 * gardée dans un cache de niveau module (borné, 100 entrées, LRU) et rendue
 * aussitôt au changement de `fetcher`, avec `loading: true` le temps du
 * rafraîchissement. Sans `cle`, le comportement actuel est inchangé. La clé
 * doit inclure l'id du projet pour ne jamais afficher des données d'un autre
 * projet.
 *
 * `cle` et `fetcher` doivent toujours changer ensemble (ils dérivent des mêmes
 * paramètres via `useMemo`) : `cle` est capturée dans la closure de l'effet,
 * sans l'ajouter aux dépendances, exactement comme `initial`.
 */
export function useResource<T>(
  fetcher: (() => Promise<T>) | null,
  initial: T,
  cle?: string,
): UseResourceResult<T> {
  const [tick, setTick] = useState(0);
  const [reponse, setReponse] = useState<Reponse<T> | null>(null);

  useEffect(() => {
    if (!fetcher) return;
    let cancelled = false;
    fetcher()
      .then((data) => {
        if (cancelled) return;
        // `cle` est capturée depuis la closure au moment où l'effet se lance :
        // elle correspond toujours au fetcher qui vient de répondre.
        if (cle !== undefined) setCached(cle, data);
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
    // `initial` et `cle` ne servent qu'en cas de succès/erreur ; les relire à
    // chaque rendu ne justifie pas de relancer la requête — et `cle` change
    // toujours avec `fetcher` puisqu'ils dérivent des mêmes paramètres.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fetcher, tick]);

  const refresh = useCallback(() => setTick((t) => t + 1), []);

  const memeRequete = reponse !== null && reponse.fetcher === fetcher;
  const aJour = memeRequete && reponse.tick === tick;

  // Donnée en cache : utilisée quand le fetcher a changé et qu'on n'a pas
  // encore reçu la réponse pour la clé courante.
  const donneeEnCache =
    cle !== undefined && fetcher !== null && !memeRequete
      ? getCached<T>(cle)
      : undefined;

  return {
    data:
      fetcher !== null && memeRequete
        ? reponse.data
        : donneeEnCache !== undefined
          ? donneeEnCache
          : initial,
    loading: fetcher !== null && !aJour,
    error: aJour ? reponse.error : null,
    refresh,
  };
}
