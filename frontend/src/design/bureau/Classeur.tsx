import { classeur } from "../../lib/bureau/sprites/communs";
import { memoise } from "../../lib/bureau/sprites/symboles";
import SpriteSvg from "./SpriteSvg";

const dessin = memoise(classeur);

/** Un classeur à tiroirs, grille 20 × 32 (30 × 48 px ; ticket-727) : porte-étiquettes, poignées, patins. Du mobilier fixe (ADR-058). */
export default function Classeur() {
  return <SpriteSvg sprite={dessin()} largeur={30} hauteur={48} data-sprite="classeur" />;
}
