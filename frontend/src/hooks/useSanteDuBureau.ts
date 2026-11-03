import { useMaintenant } from "./useMaintenant";

/** Intervalle de l'horloge du Bureau : la santé change à l'échelle de la dizaine de secondes. */
export const INTERVALLE_BUREAU_MS = 5_000;

/**
 * L'horloge unique du Bureau. La vue la monte une fois et passe `maintenant` aux
 * pièces : aucun sprite ni aucune pièce n'ouvre son propre minuteur.
 */
export function useSanteDuBureau(): number {
  return useMaintenant(INTERVALLE_BUREAU_MS);
}
