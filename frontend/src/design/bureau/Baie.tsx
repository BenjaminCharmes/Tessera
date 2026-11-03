import type { EtatDuService } from "../etatDuService";
import { petiteBaie } from "../../lib/bureau/sprites/serveurs";
import { memoise } from "../../lib/bureau/sprites/symboles";
import SpriteSvg from "./SpriteSvg";

interface BaieProps {
  /** Un étage par service déclaré, son voyant dit l'état. */
  services: readonly EtatDuService[];
}

const dessin = memoise((etats: string) => petiteBaie(etats.split(",") as EtatDuService[]));

/**
 * La petite baie de la pièce (ticket-727) : un serveur 2U par service déclaré, voyant
 * dans son logement, grille d'aération, tiroirs de disques. Grille 24 × (8 par étage + 4).
 */
export default function Baie({ services }: BaieProps) {
  const etats = services.join(",");
  return (
    <SpriteSvg
      sprite={dessin(etats)}
      largeur={36}
      hauteur={(services.length * 8 + 4) * 1.5}
      data-sprite="baie"
      data-voyants={etats}
    />
  );
}
