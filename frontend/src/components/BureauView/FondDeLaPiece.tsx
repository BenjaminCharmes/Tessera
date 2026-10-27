import MachineACafe from "../../design/bureau/MachineACafe";
import Porte from "../../design/bureau/Porte";
import Vapeur from "../../design/bureau/Vapeur";
import { MACHINE_X, PORTE_X } from "../../lib/bureau/activites";

interface FondDeLaPieceProps {
  /** Quelqu'un se sert à la machine : elle fume. Sinon, elle reste un meuble. */
  machineEnService: boolean;
}

/**
 * Le mur du fond : le coin café et la porte. Du mobilier, dessiné toujours ; la
 * seule chose qui bouge ici, la vapeur, dit un fait (un agent à la machine).
 */
export default function FondDeLaPiece({ machineEnService }: FondDeLaPieceProps) {
  return (
    <div className="relative h-18" data-fond="piece">
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
