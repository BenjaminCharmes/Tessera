import { gyrophare } from "../../lib/bureau/sprites/objets";
import { memoise } from "../../lib/bureau/sprites/symboles";
import SpriteSvg from "./SpriteSvg";

const dessin = memoise((suspendu: boolean) => gyrophare(suspendu));

/**
 * Le gyrophare d'une CI rouge, grille 20 × 16 (30 × 24 px ; ticket-727), suspendu tête
 * en bas sous le plafonnier du milieu, qui lui sert de support. Le dôme et ses éclats
 * clignotent (`anim-gyro`, coupée sous `prefers-reduced-motion`), le socle reste.
 */
export default function Gyrophare() {
  return <SpriteSvg sprite={dessin(true)} largeur={30} hauteur={24} data-sprite="gyrophare" data-suspendu />;
}
