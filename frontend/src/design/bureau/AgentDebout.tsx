import type { RoleAffiche } from "../../lib/bureau/postesDuRun";
import { TENUES, physique } from "../../lib/bureau/physique";
import Personnage from "./Personnage";

interface AgentDeboutProps {
  projet: string;
  role: RoleAffiche;
  /** Les bras levés : il fête la PR mergée. */
  brasLeves?: boolean;
  /** Les bras le long du corps, mains vides : il fait une pause. Sinon, tasse à la main. */
  sansTasse?: boolean;
  /** Une feuille annotée à la main : il rend sa copie au codeur. */
  feuille?: boolean;
}

/**
 * L'agent qui a fini, debout à côté de son poste : sa propre grille 12 × 20 en
 * 42 × 70 px, à l'échelle du personnage assis (tête de 6 unités dans les deux).
 * `overflow-visible` : les bras levés de la fête dépassent la grille.
 */
export default function AgentDebout({ projet, role, brasLeves = false, sansTasse = false, feuille = false }: AgentDeboutProps) {
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
      <Personnage pose="debout" tenue={TENUES[role]} physique={physique(projet, role)} brasLeves={brasLeves} sansTasse={sansTasse} feuille={feuille} />
    </svg>
  );
}
