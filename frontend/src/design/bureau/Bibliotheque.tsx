import { bibliotheque } from "../../lib/bureau/sprites/mobilier";
import { memoise } from "../../lib/bureau/sprites/symboles";
import SpriteSvg from "./SpriteSvg";

const dessin = memoise(bibliotheque);

/**
 * La bibliothèque, grille 32 × 36 (48 × 54 px ; ticket-727) : reliures, livres couchés,
 * une petite plante. Du mobilier fixe, sans état (ADR-058).
 */
export default function Bibliotheque() {
  return <SpriteSvg sprite={dessin()} largeur={48} hauteur={54} data-sprite="bibliotheque" />;
}
