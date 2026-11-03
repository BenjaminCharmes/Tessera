import { dossier } from "../../lib/bureau/sprites/objets";
import { memoise } from "../../lib/bureau/sprites/symboles";
import SpriteSvg from "./SpriteSvg";

const dessin = memoise(dossier);

/** Un dossier de la pile, grille 20 × 16 (ticket-727) : onglet, feuilles, étiquette du ticket. */
export default function Dossier() {
  return <SpriteSvg sprite={dessin()} largeur={20} hauteur={16} data-sprite="dossier" />;
}
