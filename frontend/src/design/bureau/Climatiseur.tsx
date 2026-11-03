import { climatiseur } from "../../lib/bureau/sprites/serveurs";
import { memoise } from "../../lib/bureau/sprites/symboles";
import SpriteSvg from "./SpriteSvg";

const dessin = memoise(climatiseur);

/**
 * Le climatiseur de salle, grille 32 × 44 (ticket-727) : lames en relief, filtre à
 * fentes, trappe de service. Du mobilier : il se dessine toujours, fixe, sans voyant.
 */
export default function Climatiseur() {
  return <SpriteSvg sprite={dessin()} largeur={48} hauteur={66} data-sprite="climatiseur" />;
}
