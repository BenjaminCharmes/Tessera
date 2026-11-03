import { vapeur } from "../../lib/bureau/sprites/objets";
import { memoise } from "../../lib/bureau/sprites/symboles";
import SpriteSvg from "./SpriteSvg";

const dessin = memoise(vapeur);

/**
 * La vapeur du café, grille 24 × 16 (ticket-727) : trois volutes qui montent chacune à
 * son rythme (`anim-vapeur`). Elle ne se pose que quand un agent est à la machine.
 */
export default function Vapeur() {
  return <SpriteSvg sprite={dessin()} largeur={28.8} hauteur={19.2} data-sprite="vapeur" />;
}
