import { porteCoupeFeu } from "../../lib/bureau/sprites/serveurs";
import { memoise } from "../../lib/bureau/sprites/symboles";
import SpriteSvg from "./SpriteSvg";

const dessin = memoise(porteCoupeFeu);

/**
 * La porte coupe-feu, grille 28 × 36 (ticket-727) : hublot armé, ferme-porte, barre
 * antipanique, lecteur de badge. Du mobilier : fixe, sans voyant — le lecteur ne rend
 * aucun état.
 */
export default function PorteCoupeFeu() {
  return <SpriteSvg sprite={dessin()} largeur={42} hauteur={54} data-sprite="porte-coupe-feu" />;
}
