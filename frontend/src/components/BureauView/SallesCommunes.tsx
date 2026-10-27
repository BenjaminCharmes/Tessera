import type { ProjetPourLaColonne } from "../../lib/bureau/aToi";
import { occupantsDeLaPause, occupantsDeLaReunion } from "../../lib/bureau/salles";
import { agentsAuDirecteur, agentsAuxRh } from "../../lib/bureau/sallesCommunes";
import BureauDuDirecteur from "./BureauDuDirecteur";
import SallePause from "./SallePause";
import SalleReunion from "./SalleReunion";
import SalleRh from "./SalleRh";

interface SallesCommunesProps {
  projets: readonly ProjetPourLaColonne[];
  /** L'horloge unique de la vue : les RH s'y mesurent, aucun minuteur n'est ouvert ici. */
  maintenant: number;
}

/**
 * Les quatre salles communes en une rangée, au-dessus des pièces des projets :
 * directeur, réunion, pause, RH. La grille `auto-fit` les passe à la ligne
 * quand la vue se resserre.
 */
export default function SallesCommunes({ projets, maintenant }: SallesCommunesProps) {
  return (
    <div className="grid grid-cols-[repeat(auto-fit,minmax(240px,1fr))] gap-3.5" data-testid="salles-communes">
      <BureauDuDirecteur agents={agentsAuDirecteur(projets, maintenant)} />
      <SalleReunion occupants={occupantsDeLaReunion(projets)} />
      <SallePause occupants={occupantsDeLaPause(projets)} />
      <SalleRh agents={agentsAuxRh(projets, maintenant)} />
    </div>
  );
}
