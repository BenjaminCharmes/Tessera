import MachineACafe from "../../design/bureau/MachineACafe";
import Porte from "../../design/bureau/Porte";
import Vapeur from "../../design/bureau/Vapeur";
import type { StreamState } from "../../hooks/streamState";
import { MACHINE_X, PORTE_X } from "../../lib/bureau/activites";
import TableauDesCriteres from "./TableauDesCriteres";

/** Le tableau blanc, accroché à gauche du mur : loin du gyrophare et de la machine. */
const TABLEAU_X = 40;

interface FondDeLaPieceProps {
  projet: string;
  etat: StreamState;
  /** Quelqu'un se sert à la machine : elle fume. Sinon, elle reste un meuble. */
  machineEnService: boolean;
}

/**
 * Le mur du fond : le tableau des critères, le coin café et la porte. Du mobilier,
 * dessiné toujours ; ce qui s'y lit ou bouge dit un fait : les critères jugés, la
 * vapeur d'un agent à la machine.
 */
export default function FondDeLaPiece({ projet, etat, machineEnService }: FondDeLaPieceProps) {
  return (
    <div className="relative h-18" data-fond="piece">
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
        <Porte />
      </span>
    </div>
  );
}
