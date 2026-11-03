import { graine } from "./physique";

/** Le nombre de tableaux que dessine le cadre. */
export const IMAGES_DU_CADRE = 4;

export type ImageDuCadre = 0 | 1 | 2 | 3;

/**
 * Le tableau accroché dans le cadre d'une pièce ou d'une salle : tiré du nom, comme la
 * tenue des agents, donc le même d'un rendu à l'autre. Du mobilier, pas un état (ADR-058).
 */
export function imageDuCadre(cle: string): ImageDuCadre {
  const i = graine(`cadre:${cle}`) % IMAGES_DU_CADRE;
  return i === 0 || i === 1 || i === 2 ? i : 3;
}
