/** Largeur du repère logique du sol, en pixels : celle de la maquette, où se calculent tous les placements. */
export const LARGEUR_DU_SOL = 800;

/** Plus petit facteur : en deçà, les sprites seraient illisibles. */
export const ECHELLE_MIN = 0.5;
/** Plus grand facteur : au-delà, le sol se centre au lieu de grossir. */
export const ECHELLE_MAX = 2;

/** Le facteur qui fait remplir `largeurDisponible` au sol de 800 px, borné entre 0,5 et 2. */
export function echelleDuSol(largeurDisponible: number): number {
  if (!Number.isFinite(largeurDisponible)) return 1;
  return Math.min(ECHELLE_MAX, Math.max(ECHELLE_MIN, largeurDisponible / LARGEUR_DU_SOL));
}
