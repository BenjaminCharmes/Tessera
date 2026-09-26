import { useMemo } from "react";
import { api } from "../lib/api";
import { useResource } from "./useResource";
import type { Limites } from "../types/api";

/** Les plafonds de dépense, lus une fois au chargement — ticket-197. */
export function useLimites(): Limites | null {
  const fetcher = useMemo(() => () => api.orchestrator.limits(), []);
  return useResource<Limites | null>(fetcher, null).data;
}
