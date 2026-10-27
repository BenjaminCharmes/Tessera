import type { PosteId } from "../../lib/bureau/postesDuRun";
import { TENUES, physique } from "../../lib/bureau/physique";
import Personnage from "./Personnage";

interface AgentDeboutProps {
  projet: string;
  role: PosteId;
}

/**
 * L'agent qui a fini, debout à côté de son poste : sa propre grille 12 × 20 en
 * 42 × 70 px, à l'échelle du personnage assis (tête de 6 unités dans les deux).
 * `overflow-visible` : le chignon dépasse la grille d'une unité.
 */
export default function AgentDebout({ projet, role }: AgentDeboutProps) {
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
      <Personnage pose="debout" tenue={TENUES[role]} physique={physique(projet, role)} />
    </svg>
  );
}
