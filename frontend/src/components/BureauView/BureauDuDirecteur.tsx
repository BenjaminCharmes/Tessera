import AgentDebout from "../../design/bureau/AgentDebout";
import BureauEnBois from "../../design/bureau/BureauEnBois";
import Bulle from "../../design/bureau/Bulle";
import { nomDuPoste } from "../../lib/bureau/libelleDuPoste";
import GoldFrame from "../../design/bureau/GoldFrame";
import { PHYSIQUE_DU_DIRECTEUR, TENUE_DU_DIRECTEUR } from "../../lib/bureau/sallesCommunes";
import type { AgentEnSalle } from "../../lib/bureau/sallesCommunes";
import { employeeLabel } from "../../lib/bureau/weekEmployee";
import type { WeekEmployee } from "../../lib/bureau/weekEmployee";
import AvecInfobulle from "./AvecInfobulle";
import Salle from "./Salle";

interface BureauDuDirecteurProps {
  /** Les agents dont le run attend une réponse : ils quittent leur poste pour se tenir devant lui. */
  agents: readonly AgentEnSalle[];
  /** L'horloge unique de la vue (ticket-602). */
  maintenant: number;
  /** L'employé de la semaine : sans lui, pas de cadre au mur. */
  employe?: WeekEmployee | null;
}

/** Le cadre doré : le texte n'est écrit nulle part, il se lit en infobulle au survol et au focus. */
function CadreDeLEmploye({ employe }: { employe: WeekEmployee }) {
  const libelle = employeeLabel(employe);
  return (
    <AvecInfobulle
      label={`Employé de la semaine : ${libelle}`}
      className="rounded-sm"
      infobulle={libelle}
    >
      <span data-employe={employe.project}>
        <GoldFrame projet={employe.project} />
      </span>
    </AvecInfobulle>
  );
}

/**
 * Le bureau du directeur : l'utilisateur, assis. Un agent dont la question
 * attend sa réponse (ADR-025) se tient devant lui, bulle « ? » au-dessus ; il
 * retourne à son poste dès que la question a sa réponse.
 */
export default function BureauDuDirecteur({ agents, maintenant, employe = null }: BureauDuDirecteurProps) {
  return (
    <Salle
      maintenant={maintenant}
      avecSoleil
      accroche={employe && <CadreDeLEmploye employe={employe} />}
      titre="Bureau du directeur"
      entete="un agent dont la question attend ta réponse vient s'y tenir"
      vide="Aucune question en attente"
      mobilier={<BureauEnBois tenue={TENUE_DU_DIRECTEUR} physique={PHYSIQUE_DU_DIRECTEUR} />}
      ambre={agents.length > 0}
    >
      {/* Un projet ne tient qu'un run à la fois (ADR-038) : un agent par projet, donc la clé est unique. */}
      {agents.map(({ projet, poste }) => (
        <li key={projet} data-agent={poste} className="flex items-end gap-2">
          <div className="flex flex-col items-center">
            <Bulle sante="question" />
            <AgentDebout projet={projet} role={poste} />
          </div>
          <span className="text-xs">
            <span className="text-zinc-400">{projet}</span> · {nomDuPoste(poste)}
          </span>
        </li>
      ))}
    </Salle>
  );
}
