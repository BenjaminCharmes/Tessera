import AgentDebout from "../../design/bureau/AgentDebout";
import BureauEnBois from "../../design/bureau/BureauEnBois";
import { IconChevronRight } from "../../design/icons";
import { nomDuPoste } from "../../lib/bureau/libelleDuPoste";
import { PHYSIQUE_DES_RH, TENUE_DES_RH } from "../../lib/bureau/sallesCommunes";
import type { AgentAuxRh } from "../../lib/bureau/sallesCommunes";
import Salle from "./Salle";

interface SalleRhProps {
  /** Les agents dont le provider a basculé sur son repli, depuis moins de 20 s. */
  agents: readonly AgentAuxRh[];
}

/**
 * Les RH : une recruteuse à son bureau. Un rôle dont le provider principal est
 * indisponible y passe avec « tenté → utilisé », puis retourne à son poste
 * (ADR-046). Le délai se lit dans `lib/bureau/sallesCommunes`.
 */
export default function SalleRh({ agents }: SalleRhProps) {
  return (
    <Salle
      titre="RH"
      entete="un rôle dont le provider est indisponible passe ici, le temps de son repli"
      vide="Aucun repli de provider"
      mobilier={<BureauEnBois tenue={TENUE_DES_RH} physique={PHYSIQUE_DES_RH} />}
      ambre={agents.length > 0}
    >
      {/* Un projet ne tient qu'un run à la fois (ADR-038) : un agent par projet, donc la clé est unique. */}
      {agents.map(({ projet, poste, tente, utilise, modele }) => (
        <li key={projet} data-agent={poste} className="flex items-end gap-2">
          <AgentDebout projet={projet} role={poste} />
          <span className="flex flex-col text-xs">
            <span>
              <span className="text-zinc-400">{projet}</span> · {nomDuPoste(poste)}
            </span>
            <span
              data-repli="tente-utilise"
              aria-label={`${tente} vers ${utilise}`}
              title={modele}
              className="flex items-center gap-0.5 text-amber-300"
            >
              <span>{tente}</span>
              <IconChevronRight size={12} />
              <span>{utilise}</span>
            </span>
          </span>
        </li>
      ))}
    </Salle>
  );
}
