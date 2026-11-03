import type { ImageDuCadre } from "../../lib/bureau/cadre";
import { cadre } from "../../lib/bureau/sprites/tableau";
import { memoise } from "../../lib/bureau/sprites/symboles";
import SpriteSvg from "./SpriteSvg";

interface CadreProps {
  /** Le tableau : tiré du nom de la pièce par `imageDuCadre`, jamais un état. */
  image: ImageDuCadre;
}

const dessin = memoise(cadre);

/**
 * Un cadre accroché au mur, grille 20 × 24 (ticket-727) : baguette en relief, toile en
 * retrait. Du mobilier fixe, sans état (ADR-058) : seule l'image varie d'une pièce à l'autre.
 */
export default function Cadre({ image }: CadreProps) {
  return <SpriteSvg sprite={dessin(image)} largeur={20} hauteur={24} data-sprite="cadre" data-image={image} />;
}
