import Agrandi from "../../design/bureau/Agrandi";
import GoldFrame from "../../design/bureau/GoldFrame";
import { employeeLabel } from "../../lib/bureau/weekEmployee";
import type { WeekEmployee } from "../../lib/bureau/weekEmployee";
import AvecInfobulle from "./AvecInfobulle";

/** Plus petit que l'échelle commune : à pleine taille, il dominait le mur de la salle. */
const ECHELLE_DU_CADRE = 0.7;

/** Le cadre doré : le texte n'est écrit nulle part, il se lit en infobulle au survol et au focus. */
export default function CadreDeLEmploye({ employe }: { employe: WeekEmployee }) {
  const libelle = employeeLabel(employe);
  return (
    <AvecInfobulle
      label={`Employé de la semaine : ${libelle}`}
      className="rounded-sm"
      infobulle={libelle}
    >
      <span data-employe={employe.project}>
        <Agrandi relatif={ECHELLE_DU_CADRE}>
          <GoldFrame projet={employe.project} />
        </Agrandi>
      </span>
    </AvecInfobulle>
  );
}
