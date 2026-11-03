import { chaise } from "../../lib/bureau/sprites/communs";
import { memoise } from "../../lib/bureau/sprites/symboles";
import SpriteSvg from "./SpriteSvg";

const dessin = memoise(chaise);

/** Une chaise en bois vue de face, grille 16 × 20 (24 × 30 px ; ticket-727) : dossier à barreaux, assise, pieds. Du mobilier fixe (ADR-058). */
export default function Chaise() {
  return <SpriteSvg sprite={dessin()} largeur={24} hauteur={30} data-sprite="chaise" />;
}
