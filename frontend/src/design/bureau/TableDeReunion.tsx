import { tableDeReunion } from "../../lib/bureau/sprites/communs";
import { memoise } from "../../lib/bureau/sprites/symboles";
import SpriteSvg from "./SpriteSvg";

const dessin = memoise(tableDeReunion);

/**
 * La table de la salle de réunion, grille 48 × 24 (72 × 36 px ; ticket-727) : plateau
 * veiné, pieds massifs. Du mobilier : ni personnage ni feuille, ce que la salle occupée
 * montre vient des occupants.
 */
export default function TableDeReunion() {
  return <SpriteSvg sprite={dessin()} largeur={72} hauteur={36} data-sprite="table-de-reunion" />;
}
