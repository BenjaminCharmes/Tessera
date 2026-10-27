/** L'échelle sur un grand écran, et le plancher en deçà duquel les sprites deviennent illisibles. */
export const ECHELLE_LARGE = 1.5;
export const ECHELLE_MIN = 0.9;

/** Ce que la vue retire à la largeur de la fenêtre : barre latérale, colonne « À toi », marges. */
const HORS_DES_SALLES = 430;
/** Ce qu'une salle garde hors de ses sprites : marges et écarts du mur. */
const MARGES_DUNE_SALLE = 48;
/** La largeur du mur le plus chargé (directeur : deux fenêtres, plafonnier, cadre, interrupteur) à l'échelle 1. */
const MUR_A_L_ECHELLE_UN = 200;

/**
 * L'échelle qui fait tenir le mur le plus chargé dans une des quatre salles de front,
 * pour une fenêtre de `largeur` pixels CSS, bornée entre 0,9 et 1,5 et arrondie au
 * vingtième : un zoom qui change à chaque pixel ferait trembler le pixel art.
 */
export function echellePourLargeur(largeur: number): number {
  if (!Number.isFinite(largeur)) return ECHELLE_LARGE;
  const salle = (largeur - HORS_DES_SALLES) / 4;
  const brute = (salle - MARGES_DUNE_SALLE) / MUR_A_L_ECHELLE_UN;
  const arrondie = Math.floor(brute * 20) / 20;
  return Math.min(ECHELLE_LARGE, Math.max(ECHELLE_MIN, arrondie));
}
