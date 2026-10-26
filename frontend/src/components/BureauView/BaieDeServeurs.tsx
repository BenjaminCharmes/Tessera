import Baie from "../../design/bureau/Baie";
import { etatDuService, libelleDeLEtat } from "../../design/etatDuService";
import { useServices } from "../../hooks/useServices";
import BoutonServices from "../Sidebar/BoutonServices";

interface BaieDeServeursProps {
  projet: string;
  /** Compteur d'événements de service de la supervision : il fait relire la liste. */
  signalServices: number;
}

/**
 * La baie : un étage par service déclaré, et le bouton de la barre latérale
 * pour lancer ou arrêter. Rien de déclaré, pas de baie (ADR-042).
 */
export default function BaieDeServeurs({ projet, signalServices }: BaieDeServeursProps) {
  const services = useServices(projet, signalServices);
  if (!services.declare) return null;

  return (
    <div role="group" aria-label="Services" className="flex items-end gap-2">
      <Baie services={services.services.map(etatDuService)} />
      <ul className="text-micro text-zinc-400">
        {services.services.map((s) => (
          <li key={s.nom}>
            {s.nom} — {libelleDeLEtat(s)}
          </li>
        ))}
      </ul>
      <BoutonServices services={services} libelleDuProjet={projet} />
    </div>
  );
}
