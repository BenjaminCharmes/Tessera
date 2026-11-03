import type { EcranId } from "../../lib/bureau/ecranDuPoste";
import { scene } from "../../lib/bureau/sprites/ecrans";
import { memoise } from "../../lib/bureau/sprites/symboles";
import SpriteSvg from "./SpriteSvg";
import type { TonDePoste } from "./tons";

interface ScenePropos {
  /** Vrai quand l'agent travaille réellement : seule condition pour animer la scène. */
  anime: boolean;
  /** La santé du run, ou l'état du poste : le ton des traits de la scène. */
  ton: TonDePoste;
}

/** Le ton d'un poste → l'état qui teinte la scène (ADR-026). */
const ETAT: Record<TonDePoste, string> = {
  actif: "actif",
  attente: "attente",
  question: "question",
  blocage_suspecte: "blocage",
  fait: "fait",
  libre: "attente",
};

const dessin = memoise((ecran: EcranId, ton: string, anime: boolean) => scene(ecran, ton, anime));

/**
 * La scène d'un écran (ticket-727), grille 12 × 8, posée sur la zone allumée de
 * l'écran du poste (26, 12) ; rien pour `allume` et `eteint`, qui n'en ont pas.
 * Code, tests et audit défilent image par image, sans déborder de l'écran.
 */
export default function EcranScene({ ecran, anime, ton }: ScenePropos & { ecran: EcranId }) {
  const sprite = dessin(ecran, ETAT[ton], anime);
  if (!sprite) return null;
  return (
    <SpriteSvg
      sprite={sprite}
      x={26}
      y={12}
      largeur={12}
      hauteur={8}
      className="overflow-hidden"
      data-ecran={ecran}
      data-anime={anime}
      data-ton={ton}
    />
  );
}
