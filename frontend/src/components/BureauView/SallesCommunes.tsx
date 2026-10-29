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
 * directeur, réunion, pause, RH. Toujours quatre de front : sur un écran étroit,
 * c'est l'échelle des sprites qui se réduit (`useEchelleDesSprites`).
 */
export default function SallesCommunes({ projets, maintenant, employe = null }: SallesCommunesProps) {
  return (
    <div className="grid grid-cols-4 gap-3.5" data-testid="salles-communes">
      <BureauDuDirecteur agents={agentsAuDirecteur(projets, maintenant)} maintenant={maintenant} />
      <SalleReunion occupants={occupantsDeLaReunion(projets)} maintenant={maintenant} />
      <SallePause occupants={occupantsDeLaPause(projets)} maintenant={maintenant} employe={employe} />
      <SalleRh agents={agentsAuxRh(projets, maintenant)} maintenant={maintenant} />
    </div>
  );
}
