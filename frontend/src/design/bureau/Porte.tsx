import { porte } from "../../lib/bureau/sprites/mur";
import { memoise } from "../../lib/bureau/sprites/symboles";
import SpriteSvg from "./SpriteSvg";

const dessin = memoise(porte);

/**
 * La porte de la pièce, grille 24 × 36 (36 × 54 px ; ticket-727) : chambranle, panneaux
 * à plate-bande, poignée en laiton. Du mobilier, sans voyant (ADR-058).
 */
export default function Porte() {
  return <SpriteSvg sprite={dessin()} largeur={36} hauteur={54} data-sprite="porte" />;
}
