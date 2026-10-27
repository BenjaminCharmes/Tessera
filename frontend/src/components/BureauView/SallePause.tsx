import type { OccupantDePause } from "../../lib/bureau/salles";
import Canape from "../../design/bureau/Canape";
import Frigo from "../../design/bureau/Frigo";
import MachineACafe from "../../design/bureau/MachineACafe";
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
}

/**
 * Ce qui n'est ni du travail ni un blocage : un quota épuisé (run clos, à
 * relancer à la main), une dépendance attendue, la CI de la phase 2.
 */
export default function SallePause({ occupants, maintenant }: SallePauseProps) {
  return (
    <Salle
      maintenant={maintenant}
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
      mobilier={
        <figure className="flex flex-col items-center gap-1">
          <MachineACafe />
          <figcaption className="text-micro text-zinc-500">café</figcaption>
        </figure>
      }
    >
      {occupants.map(({ projet, pause }) => (
        <li key={projet} className="text-xs">
          <span className="text-zinc-400">{projet}</span>{" "}
          <span className={TON[pause.motif]}>{pause.libelle}</span>
        </li>
      ))}
    </Salle>
  );
}
