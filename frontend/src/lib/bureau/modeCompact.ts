/** Au-delà de ce nombre de projets qui ont un run, la vue passe en rangées. */
export const SEUIL_MODE_COMPACT = 6;

/** Vrai quand plus de `SEUIL_MODE_COMPACT` projets ont un run (vivant ou clos, pas rangé). */
export function modeCompact(nombreDeProjetsAvecUnRun: number): boolean {
  return nombreDeProjetsAvecUnRun > SEUIL_MODE_COMPACT;
}
