import Baie from "../../design/bureau/Baie";
import { etatDuService, libelleDeLEtat } from "../../design/etatDuService";
import type { UseServicesResult } from "../../hooks/useServices";
import AvecInfobulle from "./AvecInfobulle";

interface BaieDeServeursProps {
  /** Les services du projet, lus une fois par la pièce : le bouton de l'en-tête les lance. */
  services: UseServicesResult;
}

/**
 * La baie, contre le mur : un étage par service déclaré, son voyant pour état.
 * Les noms et les états se lisent en infobulle. Rien de déclaré, pas de baie (ADR-042).
 */
export default function BaieDeServeurs({ services }: BaieDeServeursProps) {
  if (!services.declare) return null;

  return (
    <AvecInfobulle
      label="Services"
      className="block"
      infobulle={
        <ul>
          {services.services.map((s) => (
            <li key={s.nom}>
              {s.nom} <span className="text-zinc-400">— {libelleDeLEtat(s)}</span>
            </li>
          ))}
        </ul>
      }
    >
      <Baie services={services.services.map(etatDuService)} />
    </AvecInfobulle>
  );
}
