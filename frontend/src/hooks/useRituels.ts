import { useCallback, useState } from "react";
import { lireRituels, marquerFait, reporterRituel } from "../lib/apiRituels";
import type { ListeRituels, Rituel } from "../lib/apiRituels";
import { usePolling } from "./usePolling";

/** Cinq minutes : un rituel se mesure en heures. */
const CADENCE_MS = 5 * 60 * 1000;

export interface UseRituelsResult {
  rituels: Rituel[];
  /** Combien de rituels sont en retard : le nombre de la pastille. */
  enRetard: number;
  /** L'erreur du backend (lecture de `rituels.md`) ou de la requête. */
  erreur: string | null;
  fait: (id: string) => Promise<void>;
  reporter: (id: string) => Promise<void>;
}

const VIDE: ListeRituels = { rituels: [], erreur: null };

const message = (e: unknown): string => (e instanceof Error ? e.message : String(e));

/** Lit les rituels à l'ouverture puis toutes les cinq minutes (ticket-903). */
export function useRituels(): UseRituelsResult {
  const [liste, setListe] = useState<ListeRituels>(VIDE);
  const [echec, setEchec] = useState<string | null>(null);

  const lire = useCallback(async () => {
    try {
      setListe(await lireRituels());
      setEchec(null);
    } catch (e) {
      setEchec(message(e));
    }
  }, []);

  usePolling(() => void lire(), { cadenceMs: CADENCE_MS, immediat: true });

  const agir = useCallback(
    async (action: (id: string) => Promise<void>, id: string) => {
      try {
        await action(id);
      } catch (e) {
        setEchec(message(e));
        return;
      }
      await lire();
    },
    [lire],
  );

  return {
    rituels: liste.rituels,
    enRetard: liste.rituels.filter((r) => r.statut === "en_retard").length,
    erreur: liste.erreur ?? echec,
    fait: (id) => agir(marquerFait, id),
    reporter: (id) => agir(reporterRituel, id),
  };
}
