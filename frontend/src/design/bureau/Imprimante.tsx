import { imprimante } from "../../lib/bureau/sprites/objets";
import { memoise } from "../../lib/bureau/sprites/symboles";
import SpriteSvg from "./SpriteSvg";

/** La hauteur du meuble sous l'imprimante, en px : la pile de dossiers se pose dessus. */
export const HAUTEUR_DU_MEUBLE = 24;

const dessin = memoise(imprimante);

/**
 * L'imprimante sur son meuble à deux portes, grille 48 × 28 (72 × 42 px ; ticket-727) :
 * ramette, feuille imprimée, afficheur éteint. Aucun voyant (ADR-058).
 */
export default function Imprimante() {
  return <SpriteSvg sprite={dessin()} largeur={72} hauteur={42} data-sprite="imprimante" />;
}
