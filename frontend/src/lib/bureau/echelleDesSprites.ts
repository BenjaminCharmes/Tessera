/**
 * L'échelle sur un grand écran, et le plancher en deçà duquel les sprites deviennent
 * illisibles. 0,7 : en grille ×2 (ticket-727), à 0,9 le mur et le sol des salles du
 * haut débordaient sur un écran de 1280 px.
 */
export const ECHELLE_LARGE = 1.5;
export const ECHELLE_MIN = 0.7;
/** Le mobilier, un peu plus grand que les personnages : à la même échelle, il paraissait petit à côté d'eux (ticket-727). */
export const ECHELLE_DU_MOBILIER = 1.2;

/** Ce que la vue retire à la largeur de la fenêtre : barre latérale, colonne « À toi », marges. */
const HORS_DES_SALLES = 430;
/** Ce qu'une salle garde hors de ses sprites : marges et écarts du mur. */
const MARGES_DUNE_SALLE = 48;
/** La largeur du mur le plus chargé (directeur : deux fenêtres, plafonnier, cadre de l'employé, horloge, cadre, interrupteur) à l'échelle 1 (ticket-635). */
const MUR_A_L_ECHELLE_UN = 240;

/**
 * L'échelle qui fait tenir le mur le plus chargé dans une des quatre salles de front,
 * pour une fenêtre de `largeur` pixels CSS, bornée entre 0,7 et 1,5 et arrondie au
 * vingtième : un zoom qui change à chaque pixel ferait trembler le pixel art.
 */
export function echellePourLargeur(largeur: number): number {
  if (!Number.isFinite(largeur)) return ECHELLE_LARGE;
  const salle = (largeur - HORS_DES_SALLES) / 4;
  const brute = (salle - MARGES_DUNE_SALLE) / MUR_A_L_ECHELLE_UN;
  const arrondie = Math.floor(brute * 20) / 20;
  return Math.min(ECHELLE_LARGE, Math.max(ECHELLE_MIN, arrondie));
}
