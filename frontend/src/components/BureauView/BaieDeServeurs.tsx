import Agrandi from "../../design/bureau/Agrandi";
import Baie from "../../design/bureau/Baie";
import { etatDuService, libelleDeLEtat } from "../../design/etatDuService";
import type { UseServicesResult } from "../../hooks/useServices";
import { adresseDeLApp } from "../../lib/bureau/adresseDeLApp";
import AvecInfobulle from "./AvecInfobulle";

interface BaieDeServeursProps {
  /** Les services du projet, lus une fois par la pièce : le bouton de l'en-tête les lance. */
  services: UseServicesResult;
}

/**
 * La baie, contre le mur : un étage par service déclaré, son voyant pour état.
 * Les noms et les états se lisent en infobulle. Rien de déclaré, pas de baie (ADR-042).
 * Un service lancé qui a annoncé son adresse fait de la baie un raccourci vers l'app
 * (ticket-622) ; sinon, elle reste un meuble : lancer se fait depuis l'en-tête.
 */
export default function BaieDeServeurs({ services }: BaieDeServeursProps) {
  if (!services.declare) return null;
  const adresse = adresseDeLApp(services.services);

  return (
    <AvecInfobulle
      label={adresse ? `Services — ouvrir ${adresse}` : "Services"}
      className="block"
      onActiver={
        adresse
          ? () => window.open(adresse, "_blank", "noopener,noreferrer")
          : undefined
      }
      infobulle={
        <ul>
          {services.services.map((s) => (
            <li key={s.nom}>
              {s.nom}{" "}
              <span className="text-zinc-400">— {libelleDeLEtat(s)}</span>
            </li>
          ))}
        </ul>
      }
    >
      <Agrandi>
        <Baie services={services.services.map(etatDuService)} />
      </Agrandi>
    </AvecInfobulle>
  );
}
