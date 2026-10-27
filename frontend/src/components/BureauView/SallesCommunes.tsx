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
 * directeur, réunion, pause, RH. Quatre de front sur une vue large, deux par deux
 * sous 72 rem : leur mobilier ne se chevauche pas sur un écran de portable.
 */
export default function SallesCommunes({ projets, maintenant, employe = null }: SallesCommunesProps) {
  return (
    <div className="@container">
      <div className="grid grid-cols-2 gap-3.5 @6xl:grid-cols-4" data-testid="salles-communes">
        <BureauDuDirecteur agents={agentsAuDirecteur(projets, maintenant)} maintenant={maintenant} employe={employe} />
        <SalleReunion occupants={occupantsDeLaReunion(projets)} maintenant={maintenant} />
        <SallePause occupants={occupantsDeLaPause(projets)} maintenant={maintenant} />
        <SalleRh agents={agentsAuxRh(projets, maintenant)} maintenant={maintenant} />
      </div>
    </div>
  );
}
