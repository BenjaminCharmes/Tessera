import type { RoleAffiche } from "../../lib/bureau/postesDuRun";
import { TENUES, physique } from "../../lib/bureau/physique";
import type { Physique, Tenue } from "../../lib/bureau/physique";
import Personnage from "./Personnage";

/** La tenue et le physique d'une figure sans rôle de pipeline : le directeur. */
export interface FigureDeSalle {
  tenue: Tenue;
  physique: Physique;
}

interface AgentDeboutProps {
  projet: string;
  role: RoleAffiche;
  /** Les bras levés : il fête la PR mergée. */
  brasLeves?: boolean;
  /** Les bras le long du corps, mains vides : il fait une pause. Sinon, tasse à la main. */
  sansTasse?: boolean;
  /** Une feuille annotée à la main : il rend sa copie au codeur. */
  feuille?: boolean;
  /** Une figure de salle commune, à la place de la tenue du rôle (le directeur en visite). */
  figure?: FigureDeSalle;
}

/**
 * L'agent qui a fini, debout à côté de son poste : sa propre grille 12 × 20 en
 * 42 × 70 px, à l'échelle du personnage assis (tête de 6 unités dans les deux).
 * `overflow-visible` : les bras levés de la fête dépassent la grille.
 */
export default function AgentDebout({
  projet,
  role,
  brasLeves = false,
  sansTasse = false,
  feuille = false,
  figure,
}: AgentDeboutProps) {
  return (
    <svg
      width="42"
      height="70"
      viewBox="0 0 12 20"
      shapeRendering="crispEdges"
      aria-hidden="true"
      className="overflow-visible"
      data-sprite="agent-debout"
    >
      <Personnage
        pose="debout"
        tenue={figure?.tenue ?? TENUES[role]}
        physique={figure?.physique ?? physique(projet, role)}
        brasLeves={brasLeves}
        sansTasse={sansTasse}
        feuille={feuille}
      />
    </svg>
  );
}
