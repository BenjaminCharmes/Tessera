import { etagere } from "../../lib/bureau/sprites/mobilier";
import { memoise } from "../../lib/bureau/sprites/symboles";
import SpriteSvg from "./SpriteSvg";

const dessin = memoise(etagere);

/** L'étagère murale, grille 32 × 20 (ticket-727) : une plante, deux reliures, un livre couché. */
export default function Etagere() {
  return <SpriteSvg sprite={dessin()} largeur={32} hauteur={20} data-sprite="etagere" />;
}
