import { TENUES, physique } from "../../lib/bureau/physique";
import type { EtatPoste, PosteId } from "../../lib/bureau/postesDuRun";
import type { SanteAgent } from "../../lib/santeAgent";
import Ecran from "./Ecran";
import Personnage from "./Personnage";

interface PosteProps {
  /** Le projet et le rôle : ils donnent à l'agent son physique et sa tenue. */
  projet: string;
  role: PosteId;
  etat: EtatPoste;
  sante: SanteAgent;
  /** Pièce sans run : aucun personnage, un bureau et sa chaise vide (ADR-058). */
  auRepos?: boolean;
}

/** La coche d'un poste « fait » : quatre pixels verts sur l'écran. */
function Coche() {
  return (
    <g data-sprite="coche">
      <rect x="11" y="9" width="1" height="1" className="fill-green-400" />
      <rect x="12" y="10" width="1" height="1" className="fill-green-400" />
      <rect x="13" y="9" width="1" height="1" className="fill-green-400" />
      <rect x="14" y="8" width="1" height="1" className="fill-green-400" />
    </g>
  );
}

/**
 * Un poste de travail : bureau, écran et, pendant un run, son personnage — assis
 * (il attend son tour ou il travaille). Une fois fini, il se lève : il se dessine
 * à côté du poste (`AgentDebout`), la grille 16 × 18 ne le contient plus
 * (ADR-058). Pixels `rect` sur cette grille, rien d'autre.
 */
export default function Poste({ projet, role, etat, sante, auRepos = false }: PosteProps) {
  const occupe = etat === "occupe";
  const assis = !auRepos && etat !== "fait";
  const ton = occupe ? sante : etat;
  return (
    <svg
      width="56"
      height="63"
      viewBox="0 0 16 18"
      shapeRendering="crispEdges"
      aria-hidden="true"
      data-sprite="poste"
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
      <rect x="1" y="12" width="14" height="2" className="fill-zinc-600" />
      <rect x="2" y="14" width="1" height="4" className="fill-zinc-700" />
      <rect x="13" y="14" width="1" height="4" className="fill-zinc-700" />
      <Ecran ton={ton} lueur={occupe && sante === "actif"} />
      {etat === "fait" && <Coche />}
    </svg>
  );
}
