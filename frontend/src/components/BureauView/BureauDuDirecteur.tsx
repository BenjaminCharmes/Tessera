import Agrandi from "../../design/bureau/Agrandi";
import AgentDebout from "../../design/bureau/AgentDebout";
import BureauEnBois from "../../design/bureau/BureauEnBois";
import Bibliotheque from "../../design/bureau/Bibliotheque";
import Bulle from "../../design/bureau/Bulle";
import { nomDuPoste } from "../../lib/bureau/libelleDuPoste";
import { NOM_DU_DIRECTEUR, visiteur } from "../../lib/bureau/noms";
import {
  PHYSIQUE_DU_DIRECTEUR,
  TENUE_DU_DIRECTEUR,
} from "../../lib/bureau/sallesCommunes";
import type { AgentEnSalle } from "../../lib/bureau/sallesCommunes";
import Salle from "./Salle";

interface BureauDuDirecteurProps {
  /** Les agents dont le run attend une réponse : ils quittent leur poste pour se tenir devant lui. */
  agents: readonly AgentEnSalle[];
  /** L'horloge unique de la vue (ticket-602). */
  maintenant: number;
  /** Le directeur est en visite dans une pièce : son bureau reste dessiné, mais vide (ticket-661). */
  enVisite?: boolean;
}

/**
 * Le bureau du directeur : l'utilisateur, assis. Un agent dont la question
 * attend sa réponse (ADR-025) se tient devant lui, bulle « ? » au-dessus ; il
 * retourne à son poste dès que la question a sa réponse.
 */
export default function BureauDuDirecteur({
  agents,
  maintenant,
  enVisite = false,
}: BureauDuDirecteurProps) {
  const libelle = `${NOM_DU_DIRECTEUR}, directeur${enVisite ? ", en visite" : ""}`;
  return (
    <Salle
      maintenant={maintenant}
      avecSoleil
      titre="Bureau du directeur"
      entete="un agent dont la question attend ta réponse vient s'y tenir"
      vide="Aucune question en attente"
      mobilier={
        <span role="img" aria-label={libelle} title={libelle}>
          <BureauEnBois
            tenue={TENUE_DU_DIRECTEUR}
            physique={PHYSIQUE_DU_DIRECTEUR}
            vide={enVisite}
          />
        </span>
      }
      decor={<Bibliotheque />}
      plante="ficus"
      ambre={agents.length > 0}
      textes={agents.map(({ projet, poste }) => (
        <li key={projet} className="truncate">
          <span className="text-zinc-400">{projet}</span> · {nomDuPoste(poste)}
        </li>
      ))}
    >
      {/* Un projet ne tient qu'un run à la fois (ADR-038) : un agent par projet, donc la clé est unique. */}
      {agents.map(({ projet, poste }) => (
        <li
          key={projet}
          data-agent={poste}
          title={visiteur(projet, poste, nomDuPoste(poste))}
          className="flex flex-col items-center"
        >
          <Bulle sante="question" />
          <Agrandi>
            <AgentDebout projet={projet} role={poste} />
          </Agrandi>
        </li>
      ))}
    </Salle>
  );
}
