import { useMemo } from "react";
import { api } from "../lib/api";
import { apiQuota } from "../lib/quota";
import type { QuotaWindowReading, QuotaWindows } from "../lib/quota";
import type { UsageStats } from "../types/api";
import { useResource } from "./useResource";

/** Cadence de relecture : une minute, comptée sur l'horloge du Bureau (aucun minuteur de plus). */
export const RELECTURE_TABLEAU_MS = 60_000;

export interface DonneesDuTableau {
  /** Dépense du jour UTC en dollars ; `null` quand la lecture a échoué ou n'est pas revenue. */
  depense: number | null;
  /** `null` : la fenêtre n'a jamais été relevée, on ne sait pas. */
  session: QuotaWindowReading | null;
  semaine: QuotaWindowReading | null;
}

const SANS_STATS = null as UsageStats | null;
const SANS_QUOTA: QuotaWindows = { windows: {} };
// Une clé de cache garde la dernière valeur affichée pendant la relecture :
// sans elle, chaque relecture repasserait le tableau à « inconnu ».
const CLE_STATS = { projet: "bureau", ressource: "usage-stats-7" };
const CLE_QUOTA = { projet: "bureau", ressource: "usage-quota" };

/**
 * Ce que le tableau du jour affiche : la dépense du dernier point de `daily`
 * (le jour courant, en UTC) et les fenêtres `five_hour` et `seven_day`.
 * Relu à chaque minute de `maintenant` et à chaque changement de `signal`
 * (le compteur de runs clos).
 */
export function useTableauDuJour(maintenant: number, signal: number): DonneesDuTableau {
  const minute = Math.floor(maintenant / RELECTURE_TABLEAU_MS);
  // `minute` et `signal` ne servent pas dans les fetchers : leur identité est la
  // clé de la requête (voir `useResource`), et la changer est ce qui relit.
  /* eslint-disable react-hooks/exhaustive-deps */
  const lireStats = useMemo(() => () => api.usage.stats(7, null), [minute, signal]);
  const lireQuota = useMemo(() => () => apiQuota.fenetres(), [minute, signal]);
  /* eslint-enable react-hooks/exhaustive-deps */

  const { data: stats } = useResource<UsageStats | null>(lireStats, SANS_STATS, CLE_STATS);
  const { data: quota } = useResource<QuotaWindows>(lireQuota, SANS_QUOTA, CLE_QUOTA);

  // Une réponse `daily` vide est 0 dépensé, pas une erreur ; `stats` nul est inconnu.
  const depense = stats === null ? null : (stats.daily[stats.daily.length - 1]?.cost_usd ?? 0);
  return {
    depense,
    session: quota.windows.five_hour ?? null,
    semaine: quota.windows.seven_day ?? null,
  };
}
