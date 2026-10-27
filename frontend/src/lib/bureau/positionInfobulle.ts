/** Un rectangle en pixels de la fenêtre : ce que `getBoundingClientRect` en retient. */
export interface Rectangle {
  top: number;
  bottom: number;
  left: number;
}

export interface Dimensions {
  largeur: number;
  hauteur: number;
}

export interface PositionFixe {
  top: number;
  left: number;
}

const MARGE = 4;

/**
 * Où poser une infobulle en position fixe : au-dessus de l'ancre, dessous quand
 * le haut de la fenêtre la couperait, et jamais au-delà du bord droit ni gauche.
 */
export function positionInfobulle(ancre: Rectangle, infobulle: Dimensions, fenetre: Dimensions): PositionFixe {
  const auDessus = ancre.top - infobulle.hauteur - MARGE;
  const top = auDessus >= MARGE ? auDessus : ancre.bottom + MARGE;
  const gauche = Math.min(ancre.left, fenetre.largeur - infobulle.largeur - MARGE);
  return { top, left: Math.max(gauche, MARGE) };
}
