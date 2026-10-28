/** Dix-huit confettis de 4 × 6 px, comme dans la maquette. */
export const NOMBRE_DE_CONFETTIS = 18;
const LARGEUR_DU_SOL = 800;

/**
 * Abscisse et hauteur de départ de chaque confetti : répartis, pas aléatoires.
 * L'abscisse est un pourcentage de la pièce : en pixels du repère de 800 px, elle
 * laissait la moitié droite d'une pièce large sans confettis (ticket-662).
 */
export function depart(i: number): {
  left: string;
  top: number;
  delai: number;
} {
  return {
    left: `${(((i * 47 + 20) % (LARGEUR_DU_SOL - 8)) / LARGEUR_DU_SOL) * 100}%`,
    top: (i * 29) % 70,
    delai: -(i % 6) * 0.25,
  };
}
