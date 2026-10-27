import type { ReactNode } from "react";
import MachineACafe from "../../design/bureau/MachineACafe";
import Plante from "../../design/bureau/Plante";
import Porte from "../../design/bureau/Porte";
import Vapeur from "../../design/bureau/Vapeur";
import type { StreamState } from "../../hooks/streamState";
import type { UseServicesResult } from "../../hooks/useServices";
import { MACHINE_X, PORTE_X } from "../../lib/bureau/activites";
import { cielDesFenetres } from "../../lib/bureau/ciel";
import { dayMoment } from "../../lib/bureau/dayMoment";
import { enPourcentDuSol } from "../../lib/bureau/etirementDuSol";
import CeilingLamp from "../../design/bureau/CeilingLamp";
import SkyWindow from "../../design/bureau/SkyWindow";
import BaieDeServeurs from "./BaieDeServeurs";
import BoiteAuxLettres from "./BoiteAuxLettres";
import BoutonLumiere from "./BoutonLumiere";
import Dossiers from "./Dossiers";
import TableauDesCriteres from "./TableauDesCriteres";

/**
 * Les abscisses du mur, dans le repère de 800 px, de gauche à droite : le tableau
 * blanc, deux fenêtres, le ficus, la pile de dossiers, la machine, la baie, le cactus,
 * la troisième fenêtre, la boîte aux lettres, l'interrupteur et la porte. Les
 * plafonniers pendent entre elles, hors du gyrophare (au centre).
 */
const TABLEAU_X = 40;
const FENETRES_X = [196, 276, 620] as const;
const PLAFONNIERS_X = [264, 420, 600] as const;
const FICUS_X = 350;
const DOSSIERS_X = 400;
const BAIE_X = 530;
const CACTUS_X = 578;
const BOITE_X = 684;
const INTERRUPTEUR_X = PORTE_X - 24;

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
  /** Le run vivant : sans lui, pas de pile de dossiers. */
  runId: string | null;
  /** Les services du projet, lus par la pièce : la baie les montre. */
  services: UseServicesResult;
  /** Ouvre le fil du run : la pile de dossiers en est le raccourci (ticket-602). */
  onOuvrir?: (runId: string) => void;
  /** Ouvre le projet dans l'onglet Tickets : la porte en devient un bouton. Sans lui, elle reste un meuble. */
  onOpenProject?: () => void;
}

/** Un objet posé contre le mur, à une abscisse du repère : au sol, ou accroché à `bas` du sol. */
function Pose({ x, bas = "bottom-0", children }: { x: number; bas?: string; children: ReactNode }) {
  return (
    <span className={`absolute ${bas}`} style={{ left: enPourcentDuSol(x) }}>
      {children}
    </span>
  );
}

/**
 * Le mur du fond, au-dessus de la plinthe. Du mobilier, dessiné toujours ; ce qui s'y
 * lit ou bouge dit un fait : les critères jugés, l'heure du ciel, la vapeur d'un agent
 * à la machine, les tickets en file, l'état des services et de la PR. Les abscisses
 * du repère de 800 px sont posées en pourcentage : le mur suit la largeur de la pièce.
 */
export default function FondDeLaPiece({
  projet,
  etat,
  machineEnService,
  maintenant,
  allume,
  onBasculerLumiere,
  runId,
  services,
  onOuvrir,
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
        <Pose key={x} x={x} bas="top-8">
          <SkyWindow moment={moment} nuages={ciels[i]?.nuages ?? 0} />
        </Pose>
      ))}
      {PLAFONNIERS_X.map((x) => (
        <Pose key={x} x={x} bas="top-0">
          <CeilingLamp allume={allume} />
        </Pose>
      ))}
      <Pose x={TABLEAU_X} bas="top-6">
        <TableauDesCriteres projet={projet} etat={etat} />
      </Pose>
      <Pose x={FICUS_X}>
        <Plante espece="ficus" />
      </Pose>
      <Pose x={DOSSIERS_X}>
        <Dossiers projet={projet} runId={runId} etat={etat} onOuvrir={onOuvrir} />
      </Pose>
      <Pose x={MACHINE_X}>
        <MachineACafe />
      </Pose>
      {machineEnService && (
        <Pose x={MACHINE_X} bas="bottom-12">
          <Vapeur />
        </Pose>
      )}
      <Pose x={BAIE_X}>
        <BaieDeServeurs services={services} />
      </Pose>
      <Pose x={CACTUS_X}>
        <Plante espece="cactus" />
      </Pose>
      <Pose x={BOITE_X} bas="bottom-6">
        <BoiteAuxLettres projet={projet} etat={etat} />
      </Pose>
      <Pose x={INTERRUPTEUR_X} bas="bottom-7">
        <BoutonLumiere salle={projet} allume={allume} onBasculer={onBasculerLumiere} />
      </Pose>
      <Pose x={PORTE_X}>
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
      </Pose>
    </div>
  );
}
