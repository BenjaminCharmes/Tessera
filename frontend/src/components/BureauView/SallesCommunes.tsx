import type { ProjetPourLaColonne } from "../../lib/bureau/aToi";
import { occupantsDeLaPause, occupantsDeLaReunion } from "../../lib/bureau/salles";
import { agentsAuDirecteur, agentsAuxRh } from "../../lib/bureau/sallesCommunes";
import type { WeekEmployee } from "../../lib/bureau/weekEmployee";
import BureauDuDirecteur from "./BureauDuDirecteur";
import SallePause from "./SallePause";
import SalleReunion from "./SalleReunion";
import SalleRh from "./SalleRh";

interface SallesCommunesProps {
  projets: readonly ProjetPourLaColonne[];
  /** L'horloge unique de la vue : les RH s'y mesurent, aucun minuteur n'est ouvert ici. */
  maintenant: number;
  /** L'employé de la semaine, accroché au bureau du directeur (ticket-602). */
  employe?: WeekEmployee | null;
}

/**
 * Les quatre salles communes en une rangée, au-dessus des pièces des projets :
 * directeur, réunion, pause, RH. La grille `auto-fit` les passe à la ligne
 * quand la vue se resserre.
 */
export default function SallesCommunes({ projets, maintenant, employe = null }: SallesCommunesProps) {
  return (
    <div className="grid grid-cols-[repeat(auto-fit,minmax(240px,1fr))] gap-3.5" data-testid="salles-communes">
      <BureauDuDirecteur agents={agentsAuDirecteur(projets, maintenant)} maintenant={maintenant} employe={employe} />
      <SalleReunion occupants={occupantsDeLaReunion(projets)} maintenant={maintenant} />
      <SallePause occupants={occupantsDeLaPause(projets)} maintenant={maintenant} />
      <SalleRh agents={agentsAuxRh(projets, maintenant)} maintenant={maintenant} />
    </div>
  );
}
