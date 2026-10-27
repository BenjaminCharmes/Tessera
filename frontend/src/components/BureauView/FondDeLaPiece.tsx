import MachineACafe from "../../design/bureau/MachineACafe";
import Porte from "../../design/bureau/Porte";
import Vapeur from "../../design/bureau/Vapeur";
import type { StreamState } from "../../hooks/streamState";
import { MACHINE_X, PORTE_X } from "../../lib/bureau/activites";
import { cielDesFenetres } from "../../lib/bureau/ciel";
import { dayMoment } from "../../lib/bureau/dayMoment";
import { enPourcentDuSol } from "../../lib/bureau/etirementDuSol";
import CeilingLamp from "../../design/bureau/CeilingLamp";
import SkyWindow from "../../design/bureau/SkyWindow";
import BoutonLumiere from "./BoutonLumiere";
import TableauDesCriteres from "./TableauDesCriteres";

/** Le tableau blanc, accroché à gauche du mur : loin du gyrophare et de la machine. */
const TABLEAU_X = 40;
/** Les deux fenêtres, à droite du tableau ; les trois plafonniers entre elles et au-delà, hors du gyrophare. */
const FENETRES_X = [200, 300] as const;
const PLAFONNIERS_X = [264, 420, 600] as const;
/** L'interrupteur, à gauche de la porte, comme dans un vrai bureau. */
const INTERRUPTEUR_X = PORTE_X - 26;

interface FondDeLaPieceProps {
  projet: string;
  etat: StreamState;
  /** Quelqu'un se sert à la machine : elle fume. Sinon, elle reste un meuble. */
  machineEnService: boolean;
  /** L'horloge unique de la vue : le ciel des fenêtres s'y lit (ticket-602). */
  maintenant: number;
  /** Les plafonniers : allumés la nuit, ou par l'interrupteur (ticket-609). */
  allume: boolean;
  onBasculerLumiere: () => void;
  /** Ouvre le projet dans l'onglet Tickets : la porte en devient un bouton. Sans lui, elle reste un meuble. */
  onOpenProject?: () => void;
}

/**
 * Le mur du fond, au-dessus de la plinthe : le tableau des critères, deux fenêtres,
 * trois plafonniers, le coin café, l'interrupteur et la porte. Du mobilier, dessiné
 * toujours ; ce qui s'y lit ou bouge dit un fait : les critères jugés, l'heure du
 * ciel, la vapeur d'un agent à la machine. Les abscisses du repère de 800 px sont
 * posées en pourcentage : le mur suit la largeur de la pièce.
 */
export default function FondDeLaPiece({
  projet,
  etat,
  machineEnService,
  maintenant,
  allume,
  onBasculerLumiere,
  onOpenProject,
}: FondDeLaPieceProps) {
  const moment = dayMoment(maintenant);
  const ciels = cielDesFenetres(projet, FENETRES_X.length, maintenant);
  return (
    <div
      className="relative h-26 border-b-4 border-(--sprite-plinthe) bg-(--sprite-mur)"
      data-fond="piece"
      data-mur="piece"
    >
      {FENETRES_X.map((x, i) => (
        <span key={x} className="absolute top-8" style={{ left: enPourcentDuSol(x) }}>
          <SkyWindow moment={moment} nuages={ciels[i]?.nuages ?? 0} />
        </span>
      ))}
      {PLAFONNIERS_X.map((x) => (
        <span key={x} className="absolute top-0" style={{ left: enPourcentDuSol(x) }}>
          <CeilingLamp allume={allume} />
        </span>
      ))}
      <span className="absolute top-6" style={{ left: enPourcentDuSol(TABLEAU_X) }}>
        <TableauDesCriteres projet={projet} etat={etat} />
      </span>
      <span className="absolute bottom-0" style={{ left: enPourcentDuSol(MACHINE_X) }}>
        <MachineACafe />
      </span>
      {machineEnService && (
        <span className="absolute bottom-12" style={{ left: enPourcentDuSol(MACHINE_X) }}>
          <Vapeur />
        </span>
      )}
      <span className="absolute bottom-7" style={{ left: enPourcentDuSol(INTERRUPTEUR_X) }}>
        <BoutonLumiere salle={projet} allume={allume} onBasculer={onBasculerLumiere} />
      </span>
      <span className="absolute bottom-0" style={{ left: enPourcentDuSol(PORTE_X) }}>
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
