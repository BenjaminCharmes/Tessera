import { useMemo } from "react";
import type { RelevesDeQuota } from "../lib/notifQuota";
import { apiQuota } from "../lib/quota";
import type { QuotaWindows } from "../lib/quota";
import { useResource } from "./useResource";

/** Cadence de relecture du quota pour les notifications : une minute. */
const RELECTURE_QUOTA_MS = 60_000;

// `null` tant que rien n'est revenu, et en cas d'échec : un quota qu'on n'a pas
// pu lire ne dit pas « plein », il ne dit rien, et ne notifie donc rien.
const SANS_LECTURE = null as QuotaWindows | null;
const CLE_QUOTA = { projet: "notifications", ressource: "usage-quota" };

/**
 * Les relevés de quota par fenêtre, relus chaque minute (ticket-555).
 * `undefined` : pas encore lus, ce que `notificationsPour` ne prend pas pour un passage.
 */
export function useQuotaLu(maintenant: number): RelevesDeQuota | undefined {
  const minute = Math.floor(maintenant / RELECTURE_QUOTA_MS);
  // `minute` n'entre pas dans le fetcher : son identité est la clé de la requête.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const lire = useMemo(() => () => apiQuota.fenetres(), [minute]);
  const { data } = useResource<QuotaWindows | null>(lire, SANS_LECTURE, CLE_QUOTA);
  return data?.windows;
}
