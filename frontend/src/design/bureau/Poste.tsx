import { useMemo } from "react";
import { TENUES, physique } from "../../lib/bureau/physique";
import type { EcranId } from "../../lib/bureau/ecranDuPoste";
import type { EtatPoste, RoleAffiche } from "../../lib/bureau/postesDuRun";
import type { SanteAgent } from "../../lib/santeAgent";
import { type EtatEcran, type Expression, poste } from "../../lib/bureau/sprites/poste";
import EcranScene from "./EcranScenes";
import SpriteSvg from "./SpriteSvg";

interface PosteProps {
  /** Le projet et le rôle : ils donnent à l'agent son physique et sa tenue. */
  projet: string;
  role: RoleAffiche;
  etat: EtatPoste;
  sante: SanteAgent;
  /** Ce que l'écran montre (ticket-629) ; absent, l'écran se contente d'être allumé, ✓ ou éteint. */
  ecran?: EcranId;
  /** Pièce sans run : aucun personnage, un bureau et sa chaise vide (ADR-058). */
  auRepos?: boolean;
  /** Run clos : l'agent est parti par la porte, la chaise reste vide. */
  parti?: boolean;
}

/** L'écran par défaut, quand la pièce n'en dit pas plus : allumé s'il travaille, ✓ s'il a fini, éteint sinon. */
function ecranParDefaut(etat: EtatPoste): EcranId {
  if (etat === "occupe") return "allume";
  return etat === "fait" ? "ok" : "eteint";
}

const EXPRESSION: Record<SanteAgent, Expression> = {
  actif: "actif",
  attente: "attente",
  question: "question",
  blocage_suspecte: "blocage",
};

const ECRAN: Record<SanteAgent | "fait" | "libre", EtatEcran> = {
  actif: "actif",
  attente: "attente",
  question: "question",
  blocage_suspecte: "blocage",
  fait: "fait",
  libre: "attente",
};

/**
 * Un poste de travail : bureau, écran et, pendant un run, son personnage assis (il
 * attend son tour ou il travaille). Une fois fini, il se lève : il se dessine à côté
 * du poste (`AgentDebout`), la chaise reste vide (ADR-058). Grille 40 × 36 de
 * l'atelier (ticket-727), à la même taille que l'ancienne 20 × 18. La scène de
 * l'écran (code, tests, diff…) se pose sur sa zone allumée, à l'échelle ×2.
 */
export default function Poste({
  projet,
  role,
  etat,
  sante,
  ecran = ecranParDefaut(etat),
  auRepos = false,
  parti = false,
}: PosteProps) {
  const occupe = etat === "occupe";
  const assis = !auRepos && !parti && etat !== "fait";
  const ton = occupe ? sante : etat;
  const scene = ecran !== "allume" && ecran !== "eteint";
  const anime = occupe && sante === "actif";
  const dessin = useMemo(
    () =>
      poste({
        physique: physique(projet, role),
        tenue: TENUES[role],
        vide: !assis,
        expression: occupe ? EXPRESSION[sante] : "neutre",
        tape: anime,
        etatEcran: ECRAN[ton],
        scene,
      }),
    [projet, role, assis, occupe, sante, anime, ton, scene],
  );
  return (
    <SpriteSvg sprite={dessin} largeur={70} hauteur={63} data-sprite="poste">
      {scene && <EcranScene ecran={ecran} anime={anime} ton={ton} />}
    </SpriteSvg>
  );
}
