/** Largeur du repère logique du sol, en pixels : celle de la maquette, où se calculent tous les placements. */
export const LARGEUR_DU_SOL = 800;

/** Plus petit facteur : en deçà, les postes se chevaucheraient. */
export const ETIREMENT_MIN = 0.75;

/**
 * Le facteur qui étire les abscisses du repère de 800 px sur `largeurDisponible`.
 * Les sprites gardent leur taille, la même que dans les salles communes : seul
 * l'espacement suit la largeur de la pièce.
 */
export function etirementDuSol(largeurDisponible: number): number {
  if (!Number.isFinite(largeurDisponible) || largeurDisponible <= 0) return 1;
  return Math.max(ETIREMENT_MIN, largeurDisponible / LARGEUR_DU_SOL);
}

/** Une abscisse du repère de 800 px, en pourcentage de la largeur réelle du sol. */
export function enPourcentDuSol(x: number): string {
  return `${(x / LARGEUR_DU_SOL) * 100}%`;
}
