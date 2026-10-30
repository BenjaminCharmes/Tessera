import { useEffect, useState } from "react";
import { lireActivite } from "../lib/apiActivite";
import { useFenetreVisible } from "./useFenetreVisible";
import type { ActiviteDeService } from "../types/activiteProduit";

/** À quelle cadence on relit les fichiers d'activité — ticket-673. */
export const CADENCE_ACTIVITE_MS = 5_000;

const AUCUNE: ActiviteDeService[] = [];

/**
 * L'activité des agents de produit, relue toutes les 5 s — ticket-673, ADR-064.
 *
 * Échoue fermé : une erreur de lecture ou une réponse qui n'est pas une liste
 * rend la liste vide, et non la dernière donnée connue. Un agent dessiné doit
 * correspondre à un fichier lu à l'instant (ADR-058) ; le minuteur se suspend
 * quand la fenêtre est cachée (ticket-356).
 */
export function useActiviteProduit(): ActiviteDeService[] {
  const [activite, setActivite] = useState<ActiviteDeService[]>(AUCUNE);
  const [tick, setTick] = useState(0);
  const fenetreVisible = useFenetreVisible();

  useEffect(() => {
    let annule = false;
    lireActivite()
      .then((lues) => {
        if (!annule) setActivite(Array.isArray(lues) ? lues : AUCUNE);
      })
      .catch(() => {
        if (!annule) setActivite(AUCUNE);
      });
    return () => {
      annule = true;
    };
  }, [tick]);

  useEffect(() => {
    if (!fenetreVisible) return;
    const minuteur = setInterval(() => setTick((t) => t + 1), CADENCE_ACTIVITE_MS);
    return () => clearInterval(minuteur);
  }, [fenetreVisible]);

  return activite;
}

/** Les agents déclarés par le service `service` du projet ; aucun si la réponse n'en parle pas. */
export function agentsDuService(
  activite: readonly ActiviteDeService[],
  projectId: string,
  service: string,
): ActiviteDeService["agents"] {
  const entree = activite.find((a) => a.project_id === projectId && a.service === service);
  return Array.isArray(entree?.agents) ? entree.agents : [];
}
