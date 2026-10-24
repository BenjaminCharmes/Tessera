import type { EtatDuService } from "../etatDuService";
import { TON_VOYANT } from "./tons";

interface BaieProps {
  /** Un étage par service déclaré, son voyant dit l'état. */
  services: readonly EtatDuService[];
}

/** La baie de serveurs : autant d'étages que de services déclarés. Grille 12 × (4 par étage + 2). */
export default function Baie({ services }: BaieProps) {
  const hauteur = services.length * 4 + 2;
  return (
    <svg
      width="36"
      height={hauteur * 3}
      viewBox={`0 0 12 ${hauteur}`}
      shapeRendering="crispEdges"
      aria-hidden="true"
      data-sprite="baie"
    >
      <rect x="0" y="0" width="12" height={hauteur} className="fill-zinc-700" />
      {services.map((etat, i) => (
        <g key={i} data-voyant={etat}>
          <rect x="1" y={1 + i * 4} width="10" height="3" className="fill-zinc-800" />
          <rect x="2" y={2 + i * 4} width="1" height="1" className={TON_VOYANT[etat]} />
        </g>
      ))}
    </svg>
  );
}
