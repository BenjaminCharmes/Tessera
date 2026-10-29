import { TENUES, physique } from "../../lib/bureau/physique";
import type { EcranId } from "../../lib/bureau/ecranDuPoste";
import type { EtatPoste, RoleAffiche } from "../../lib/bureau/postesDuRun";
import type { SanteAgent } from "../../lib/santeAgent";
import Ecran from "./Ecran";
import Personnage from "./Personnage";

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

/**
 * Un poste de travail : bureau, écran et, pendant un run, son personnage — assis
 * (il attend son tour ou il travaille). Une fois fini, il se lève : il se dessine
 * à côté du poste (`AgentDebout`), la grille 20 × 18 ne le contient plus
 * (ADR-058). Pixels `rect` sur cette grille, rien d'autre.
 * `overflow-visible` : les cheveux du personnage assis montent au-dessus de la grille ;
 * sans cela le `<svg>` couperait leur première ligne.
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
  return (
    <svg
      width="70"
      height="63"
      viewBox="0 0 20 18"
      shapeRendering="crispEdges"
      aria-hidden="true"
      data-sprite="poste"
      className="overflow-visible"
    >
      {assis ? (
        <Personnage
          tenue={TENUES[role]}
          physique={physique(projet, role)}
          tape={occupe && sante === "actif"}
        />
      ) : (
        <rect x="5" y="6" width="6" height="6" className="fill-zinc-800" />
      )}
      <rect x="1" y="12" width="18" height="2" className="fill-zinc-600" />
      <rect x="2" y="14" width="1" height="4" className="fill-zinc-700" />
      <rect x="17" y="14" width="1" height="4" className="fill-zinc-700" />
      <Ecran ecran={ecran} ton={ton} anime={occupe && sante === "actif"} />
    </svg>
  );
}
