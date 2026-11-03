import type { OccupantDePause } from "../../lib/bureau/salles";
import Canape from "../../design/bureau/Canape";
import Frigo from "../../design/bureau/Frigo";
import MachineACafe from "../../design/bureau/MachineACafe";
import type { WeekEmployee } from "../../lib/bureau/weekEmployee";
import CadreDeLEmploye from "./CadreDeLEmploye";
import Salle from "./Salle";

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
    />
  );
}
