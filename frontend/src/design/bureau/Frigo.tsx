import { frigo } from "../../lib/bureau/sprites/communs";
import { memoise } from "../../lib/bureau/sprites/symboles";
import SpriteSvg from "./SpriteSvg";

const dessin = memoise(frigo);

/** Un réfrigérateur, grille 20 × 36 (30 × 54 px ; ticket-727) : deux portes, poignées, un post-it. Du mobilier fixe (ADR-058). */
export default function Frigo() {
  return <SpriteSvg sprite={dessin()} largeur={30} hauteur={54} data-sprite="frigo" />;
}
