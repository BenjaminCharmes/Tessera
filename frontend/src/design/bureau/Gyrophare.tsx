import { gyrophare } from "../../lib/bureau/sprites/objets";
import { memoise } from "../../lib/bureau/sprites/symboles";
import SpriteSvg from "./SpriteSvg";

const dessin = memoise(gyrophare);

/**
 * Le gyrophare d'une CI rouge, grille 20 × 16 (30 × 24 px ; ticket-727) : le dôme et ses
 * éclats clignotent (`anim-gyro`, coupée sous `prefers-reduced-motion`), le socle reste.
 */
export default function Gyrophare() {
  return <SpriteSvg sprite={dessin()} largeur={30} hauteur={24} data-sprite="gyrophare" />;
}
