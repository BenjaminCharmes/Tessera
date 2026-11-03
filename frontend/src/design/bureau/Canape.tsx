import { canape } from "../../lib/bureau/sprites/communs";
import { memoise } from "../../lib/bureau/sprites/symboles";
import SpriteSvg from "./SpriteSvg";

const dessin = memoise(canape);

/** Un canapé, grille 48 × 20 (72 × 30 px ; ticket-727) : coussins capitonnés, accoudoirs, pieds en bois. Du mobilier fixe (ADR-058). */
export default function Canape() {
  return <SpriteSvg sprite={dessin()} largeur={72} hauteur={30} data-sprite="canape" />;
}
