import type { OccupantDePause } from "../../lib/bureau/salles";
import Agrandi from "../../design/bureau/Agrandi";
import AgentDebout from "../../design/bureau/AgentDebout";
import Canape from "../../design/bureau/Canape";
import Frigo from "../../design/bureau/Frigo";
import MachineACafe from "../../design/bureau/MachineACafe";
import { nomDuPoste } from "../../lib/bureau/libelleDuPoste";
import { visiteur } from "../../lib/bureau/noms";
import type { PosteId } from "../../lib/bureau/postesDuRun";
import type { WeekEmployee } from "../../lib/bureau/weekEmployee";
import CadreDeLEmploye from "./CadreDeLEmploye";
import Salle from "./Salle";

/**
 * Qui vient en salle de pause, selon ce que le run attend (ticket-784) : le validateur
 * qui a approuvé la livraison, la PR en main, pendant la CI ; le codeur et le reviewer,
 * tasse en main, le temps que le quota revienne ; le codeur, devant la machine, tant
 * qu'une dépendance n'est pas mergée. Chacun vient d'un état du run (ADR-058).
 */
const OCCUPANTS: Record<OccupantDePause["pause"]["motif"], { poste: PosteId; pr: boolean }[]> = {
  ci: [{ poste: "validateur", pr: true }],
  quota: [
    { poste: "codeur", pr: false },
    { poste: "reviewer", pr: false },
  ],
  dependance: [{ poste: "codeur", pr: false }],
};

const TON: Record<OccupantDePause["pause"]["motif"], string> = {
  quota: "text-amber-300",
  dependance: "text-zinc-300",
  ci: "text-blue-300",
};

interface SallePauseProps {
  occupants: readonly OccupantDePause[];
  /** L'horloge unique de la vue (ticket-602). */
  maintenant: number;
  /** L'employé de la semaine : sans lui, pas de cadre au mur. Accroché ici, le bureau du directeur débordait. */
  employe?: WeekEmployee | null;
}

/**
 * Ce qui n'est ni du travail ni un blocage : un quota épuisé (run clos, à
 * relancer à la main), une dépendance attendue, la CI de la phase 2.
 */
export default function SallePause({ occupants, maintenant, employe = null }: SallePauseProps) {
  return (
    <Salle
      maintenant={maintenant}
      accroche={employe && <CadreDeLEmploye employe={employe} />}
      titre="Salle de pause"
      entete="un run qui attend quelque chose d'extérieur : quota, CI, une dépendance"
      vide="Personne en pause"
      decor={
        <>
          <Canape />
          <Frigo />
        </>
      }
      plante="cactus"
      mobilier={<MachineACafe />}
      textes={occupants.map(({ projet, pause }) => (
        <li key={projet} className="truncate">
          <span className="text-zinc-400">{projet}</span>{" "}
          <span className={TON[pause.motif]}>{pause.libelle}</span>
        </li>
      ))}
    >
      {occupants.flatMap(({ projet, pause }) =>
        OCCUPANTS[pause.motif].map(({ poste, pr }) => (
          <li
            key={`${projet}-${poste}`}
            data-agent={poste}
            data-objet={pr ? "pr" : undefined}
            title={`${visiteur(projet, poste, nomDuPoste(poste))} — ${pause.libelle}`}
          >
            <Agrandi>
              <AgentDebout projet={projet} role={poste} feuille={pr} sansTasse={pr} />
            </Agrandi>
          </li>
        )),
      )}
    </Salle>
  );
}
