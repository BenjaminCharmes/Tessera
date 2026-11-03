import { pupitreVide } from "../../lib/bureau/sprites/produit";
import { memoise } from "../../lib/bureau/sprites/symboles";
import SpriteSvg from "./SpriteSvg";

const dessin = memoise(pupitreVide);

/**
 * Un pupitre de console sans personne, écran éteint (ticket-730, ticket-727) : la
 * salle d'un produit qui ne déclare aucun agent. Du mobilier (ADR-058) : il ne
 * s'anime pas et ne porte aucun voyant. Même grille 40 × 36 que `AgentAuPupitre`.
 */
export default function PosteVide() {
  return <SpriteSvg sprite={dessin()} largeur={70} hauteur={63} className="opacity-60" data-sprite="poste-vide" data-ecran="eteint" />;
}
