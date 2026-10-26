import type { OccupantDePause } from "../../lib/bureau/salles";
import Salle from "./Salle";

const TON: Record<OccupantDePause["pause"]["motif"], string> = {
  quota: "text-amber-300",
  dependance: "text-zinc-300",
  ci: "text-blue-300",
};

interface SallePauseProps {
  occupants: readonly OccupantDePause[];
}

/**
 * Ce qui n'est ni du travail ni un blocage : un quota épuisé (run clos, à
 * relancer à la main), une dépendance attendue, la CI de la phase 2.
 */
export default function SallePause({ occupants }: SallePauseProps) {
  return (
    <Salle titre="Salle de pause" vide="Personne en pause">
      {occupants.map(({ projet, pause }) => (
        <li key={projet} className="text-xs">
          <span className="text-zinc-400">{projet}</span>{" "}
          <span className={TON[pause.motif]}>{pause.libelle}</span>
        </li>
      ))}
    </Salle>
  );
}
