import type { Physique } from "../../lib/bureau/physique";
import Console from "./Console";
import Tete from "./Tete";

interface AgentAuPupitreProps {
  physique: Physique;
  /** `actif` : les mains tapent sur le pupitre. `repos` : les bras le long du corps, posé. */
  etat: "actif" | "repos";
}

/**
 * Un agent de produit devant sa console, grille 20 × 18 (ticket-673). Le physique
 * vient de son `id`, jamais de l'état. Au travail, les bras vont au pupitre et
 * tapent (`anim-tape`, coupée sous `prefers-reduced-motion`) ; au repos, ils
 * pendent, l'agent est estompé et rien ne bouge. `overflow-visible` : les cheveux
 * montent au-dessus de la grille.
 */
export default function AgentAuPupitre({ physique, etat }: AgentAuPupitreProps) {
  const actif = etat === "actif";
  return (
    <svg
      width="70"
      height="63"
      viewBox="0 0 20 18"
      shapeRendering="crispEdges"
      aria-hidden="true"
      data-sprite="agent-de-produit"
      data-etat={etat}
      className="overflow-visible"
    >
      <g className={actif ? undefined : "opacity-60"}>
        <Tete physique={physique} x={4} y={3} />
        <rect x="3" y="7" width="8" height="5" className="fill-(--sprite-haut-produit)" />
        {actif ? (
          <g data-bras="pupitre" className="anim-tape">
            <rect x="2" y="9" width="2" height="3" className="fill-(--sprite-haut-produit-ombre)" />
            <rect x="10" y="9" width="2" height="3" className="fill-(--sprite-haut-produit-ombre)" />
          </g>
        ) : (
          <g data-bras="repos">
            <rect x="2" y="8" width="1" height="4" className="fill-(--sprite-haut-produit-ombre)" />
            <rect x="11" y="8" width="1" height="4" className="fill-(--sprite-haut-produit-ombre)" />
          </g>
        )}
      </g>
      <Console allume={actif} />
    </svg>
  );
}
