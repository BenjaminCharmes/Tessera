/**
 * L'échelle sur un grand écran, et le plancher en deçà duquel les sprites deviennent
 * illisibles. 0,7 : en grille ×2 (ticket-727), à 0,9 le mur et le sol des salles du
 * haut débordaient sur un écran de 1280 px. 1,3 et non plus 1,5 : à 1,5, tout
 * paraissait trop gros sur un 27 pouces (ticket-898).
 */
export const ECHELLE_LARGE = 1.3;
export const ECHELLE_MIN = 0.7;
/** L'échelle à laquelle les décalages des agents (`activites.ts`) ont été réglés : ils se proportionnent à elle (ticket-898). */
export const ECHELLE_DES_DECALAGES = 1.5;
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
 * pour une fenêtre de `largeur` pixels CSS, bornée entre 0,7 et 1,3 et arrondie au
 * vingtième : un zoom qui change à chaque pixel ferait trembler le pixel art.
 */
export function echellePourLargeur(largeur: number): number {
  if (!Number.isFinite(largeur)) return ECHELLE_LARGE;
  const salle = (largeur - HORS_DES_SALLES) / 4;
  const brute = (salle - MARGES_DUNE_SALLE) / MUR_A_L_ECHELLE_UN;
  const arrondie = Math.floor(brute * 20) / 20;
  return Math.min(ECHELLE_LARGE, Math.max(ECHELLE_MIN, arrondie));
}

/**
 * Le multiple de l'échelle commune que prend la pièce d'un run : elle s'étend sur la
 * largeur des quatre salles du haut, et ses objets sont posés à des abscisses relatives.
 * À l'échelle commune, bornée par une seule de ces salles, son mobilier paraissait
 * minuscule sur un portable alors qu'elle avait toute la place ; à 1,5 fois, tout y
 * paraissait trop gros (ticket-898).
 */
export const FACTEUR_DE_LA_PIECE = 1.2;

/** L'échelle de la pièce d'un run, pour une échelle commune donnée : plafonnée à `ECHELLE_LARGE`, au vingtième. */
export function echelleDeLaPiece(echelleCommune: number): number {
  const brute = echelleCommune * FACTEUR_DE_LA_PIECE;
  return Math.min(ECHELLE_LARGE, Math.floor(brute * 20 + 1e-9) / 20);
}
