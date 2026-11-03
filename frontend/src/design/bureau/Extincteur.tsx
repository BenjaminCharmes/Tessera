import { extincteur } from "../../lib/bureau/sprites/serveurs";
import { memoise } from "../../lib/bureau/sprites/symboles";
import SpriteSvg from "./SpriteSvg";

const dessin = memoise(extincteur);

/**
 * L'extincteur, posé contre le mur, grille 12 × 28 (ticket-727). Du mobilier : fixe,
 * sans voyant. Son rouge est une famille de sprite, pas une teinte d'état.
 */
export default function Extincteur() {
  return <SpriteSvg sprite={dessin()} largeur={18} hauteur={42} data-sprite="extincteur" />;
}
