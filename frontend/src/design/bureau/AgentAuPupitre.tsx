import type { Physique } from "../../lib/bureau/physique";
import { agentAuPupitre } from "../../lib/bureau/sprites/produit";
import { memoise } from "../../lib/bureau/sprites/symboles";
import SpriteSvg from "./SpriteSvg";

interface AgentAuPupitreProps {
  physique: Physique;
  /** `actif` : les mains tapent sur le pupitre. `repos` : les bras le long du corps, posé. */
  etat: "actif" | "repos";
}

const dessin = memoise((cle: string, etat: "actif" | "repos") => agentAuPupitre(JSON.parse(cle) as Physique, etat));

/**
 * Un agent de produit devant sa console, grille 40 × 36 comme un poste du Bureau
 * (ticket-673, ticket-727). Le physique vient de son `id`, jamais de l'état. Au
 * travail, ses mains tapent et l'écran fait défiler son texte ; au
 * repos, ses bras pendent, rien ne bouge, l'écran montre trois points de veille.
 */
export default function AgentAuPupitre({ physique, etat }: AgentAuPupitreProps) {
  const actif = etat === "actif";
  return (
    <SpriteSvg
      sprite={dessin(JSON.stringify(physique), etat)}
      largeur={70}
      hauteur={63}
      data-sprite="agent-de-produit"
      data-etat={etat}
      data-bras={actif ? "pupitre" : "repos"}
      data-ecran={actif ? "allume" : "attente"}
    />
  );
}
