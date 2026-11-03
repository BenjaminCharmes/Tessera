import type { EtatDuService } from "../etatDuService";
import { baieHaute } from "../../lib/bureau/sprites/serveurs";
import { memoise } from "../../lib/bureau/sprites/symboles";
import SpriteSvg from "./SpriteSvg";

interface BaieHauteProps {
  /** L'état du service : son voyant le dit, seul élément de la baie qui porte un état. */
  etat: EtatDuService;
}

const dessin = memoise(baieHaute);

/**
 * La baie haute de la salle des serveurs, grille 24 × 60 (36 × 90 px ; ticket-727) :
 * sept serveurs 1U et un voyant. Un service, une baie. Le corps est du mobilier ; seul
 * le voyant rend un état (ADR-058), et tant que le service tourne, une diode par
 * serveur clignote.
 */
export default function BaieHaute({ etat }: BaieHauteProps) {
  return <SpriteSvg sprite={dessin(etat)} largeur={36} hauteur={90} data-sprite="baie-haute" data-voyant={etat} />;
}
