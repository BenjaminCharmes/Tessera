import type { EtatPoste } from "../../lib/bureau/postesDuRun";
import type { SanteAgent } from "../../lib/santeAgent";
import Ecran from "./Ecran";
import Personnage from "./Personnage";

interface PosteProps {
  etat: EtatPoste;
  sante: SanteAgent;
}

/** Le coche d'un poste « fait » : quatre pixels verts sur le bureau. */
function Coche() {
  return (
    <g data-sprite="coche">
      <rect x="3" y="10" width="1" height="1" className="fill-green-400" />
      <rect x="4" y="11" width="1" height="1" className="fill-green-400" />
      <rect x="5" y="10" width="1" height="1" className="fill-green-400" />
      <rect x="6" y="9" width="1" height="1" className="fill-green-400" />
    </g>
  );
}

/**
 * Un poste de travail : bureau, écran, et un personnage seulement s'il est
 * occupé (ADR-058). Pixels `rect` sur une grille 16 × 18, rien d'autre.
 */
export default function Poste({ etat, sante }: PosteProps) {
  const occupe = etat === "occupe";
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
      {occupe ? (
        <Personnage tape={sante === "actif"} />
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
