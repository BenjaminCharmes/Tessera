import { useCallback } from "react";
import { FILTRES_VIDES, type FiltresTickets } from "../lib/filtresTickets";
import { useEtatPersistant } from "./useEtatPersistant";

/**
 * Les filtres de la liste et du Kanban, mémorisés **par projet** — ticket-195.
 *
 * Une seule source d'état pour les deux vues : ce qu'on cache dans la liste
 * est caché dans le tableau. Mémorisés avec le mécanisme du ticket-193,
 * pour ne pas les re-poser à chaque ouverture.
 */
type ParProjet = Record<string, FiltresTickets>;

function estParProjet(v: unknown): v is ParProjet {
  return typeof v === "object" && v !== null && !Array.isArray(v);
}

export function useFiltresTickets(projectId: string | null): {
  filtres: FiltresTickets;
  setFiltres: (f: FiltresTickets) => void;
} {
  const [parProjet, setParProjet] = useEtatPersistant<ParProjet>(
    "filtres-tickets",
    {},
    estParProjet,
  );
  const cle = projectId ?? "";
  const filtres = { ...FILTRES_VIDES, ...(parProjet[cle] ?? {}) };
  const setFiltres = useCallback(
    (f: FiltresTickets) => setParProjet((prev) => ({ ...prev, [cle]: f })),
    [cle, setParProjet],
  );
  return { filtres, setFiltres };
}
