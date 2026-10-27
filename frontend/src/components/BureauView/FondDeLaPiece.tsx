import MachineACafe from "../../design/bureau/MachineACafe";
import Porte from "../../design/bureau/Porte";
import Vapeur from "../../design/bureau/Vapeur";
import type { StreamState } from "../../hooks/streamState";
import { MACHINE_X, PORTE_X } from "../../lib/bureau/activites";
import { dayMoment } from "../../lib/bureau/dayMoment";
import CeilingLamp from "../../design/bureau/CeilingLamp";
import SkyWindow from "../../design/bureau/SkyWindow";
import TableauDesCriteres from "./TableauDesCriteres";

/** Le tableau blanc, accroché à gauche du mur : loin du gyrophare et de la machine. */
const TABLEAU_X = 40;
/** Les deux fenêtres, à droite du tableau ; les trois plafonniers entre elles et au-delà, hors du gyrophare. */
const FENETRES_X = [200, 300] as const;
const PLAFONNIERS_X = [264, 420, 600] as const;

interface FondDeLaPieceProps {
  projet: string;
  etat: StreamState;
  /** Quelqu'un se sert à la machine : elle fume. Sinon, elle reste un meuble. */
  machineEnService: boolean;
  /** L'horloge unique de la vue : le ciel des fenêtres et les plafonniers s'y lisent (ticket-602). */
  maintenant: number;
  /** Ouvre le projet dans l'onglet Tickets : la porte en devient un bouton. Sans lui, elle reste un meuble. */
  onOpenProject?: () => void;
}

/**
 * Le mur du fond : le tableau des critères, deux fenêtres, trois plafonniers, le coin café
 * et la porte. Du mobilier, dessiné toujours ; ce qui s'y lit ou bouge dit un fait : les
 * critères jugés, l'heure du ciel, la vapeur d'un agent à la machine.
 */
export default function FondDeLaPiece({
  projet,
  etat,
  machineEnService,
  maintenant,
  onOpenProject,
}: FondDeLaPieceProps) {
  const moment = dayMoment(maintenant);
  return (
    <div className="relative h-18" data-fond="piece">
      {FENETRES_X.map((x) => (
        <span key={x} className="absolute top-3" style={{ left: x }}>
          <SkyWindow moment={moment} />
        </span>
      ))}
      {PLAFONNIERS_X.map((x) => (
        <span key={x} className="absolute top-0" style={{ left: x }}>
          <CeilingLamp allume={moment === "nuit"} />
        </span>
      ))}
      <span className="absolute top-3" style={{ left: TABLEAU_X }}>
        <TableauDesCriteres projet={projet} etat={etat} />
      </span>
      <span className="absolute bottom-0" style={{ left: MACHINE_X }}>
        <MachineACafe />
      </span>
      {machineEnService && (
        <span className="absolute bottom-12" style={{ left: MACHINE_X }}>
          <Vapeur />
        </span>
      )}
      <span className="absolute bottom-0" style={{ left: PORTE_X }}>
        {onOpenProject ? (
          <button
            type="button"
            aria-label={`Ouvrir le projet ${projet}`}
            onClick={onOpenProject}
            className="block cursor-pointer rounded-sm focus-visible:outline-2 focus-visible:outline-violet-500"
          >
            <Porte />
          </button>
        ) : (
          <Porte />
        )}
      </span>
    </div>
  );
}
