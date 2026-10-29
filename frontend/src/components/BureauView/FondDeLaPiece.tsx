import Agrandi from "../../design/bureau/Agrandi";
import Bibliotheque from "../../design/bureau/Bibliotheque";
import Corbeille from "../../design/bureau/Corbeille";
import Etagere from "../../design/bureau/Etagere";
import Imprimante, { HAUTEUR_DU_MEUBLE } from "../../design/bureau/Imprimante";
import MachineACafe from "../../design/bureau/MachineACafe";
import Plante from "../../design/bureau/Plante";
import Porte from "../../design/bureau/Porte";
import Vapeur from "../../design/bureau/Vapeur";
import type { StreamState } from "../../hooks/streamState";
import { useEchelleDesSprites } from "../../hooks/useEchelleDesSprites";
import type { UseServicesResult } from "../../hooks/useServices";
import { BIBLIOTHEQUE_X, BOITE_X, MACHINE_X, PORTE_X, TABLEAU_X } from "../../lib/bureau/activites";
import { cielDesFenetres } from "../../lib/bureau/ciel";
import { boulesDeLaCorbeille } from "../../lib/bureau/corbeille";
import { dayMoment } from "../../lib/bureau/dayMoment";
import BaieDeServeurs from "./BaieDeServeurs";
import BoiteAuxLettres from "./BoiteAuxLettres";
import Dossiers from "./Dossiers";
import MurLumineux from "./MurLumineux";
import type { AbscissesDuMur } from "./MurLumineux";
import Pose from "./Pose";
import TableauDesCriteres from "./TableauDesCriteres";

/**
 * Les abscisses du mur, dans le repère de 800 px, de gauche à droite : le tableau
 * blanc, deux fenêtres, le ficus, le meuble de l'imprimante et sa pile de dossiers,
 * la machine, la baie, le cactus, la troisième fenêtre, la boîte aux lettres,
 * l'interrupteur et la porte. Les plafonniers pendent entre elles, hors du gyrophare.
 * L'abscisse du tableau vient de `activites.ts` : l'agent du plan s'y tient (ticket-623).
 */
// Fenêtre, bibliothèque, fenêtre, à intervalles égaux entre le tableau et le ficus (ticket-627).
const FENETRES_X = [134, 274, 616] as const;
const PLAFONNIERS_X = [250, 432, 590] as const;
const FICUS_X = 348;
const IMPRIMANTE_X = 392;
const BAIE_X = 528;
const CACTUS_X = 572;
// Plus près de la porte que de la boîte aux lettres, comme un vrai interrupteur (ticket-627).
const INTERRUPTEUR_X = 727;
// Au-dessus de la machine, où le mur est libre ; le cadre, à droite de la dernière fenêtre (ticket-635).
const HORLOGE_X = 488;
const CADRE_X = 684;
// À hauteur des fenêtres, sur le mur libre entre le ficus et l'horloge : sous une
// fenêtre, elle se lisait comme un rebord.
const ETAGERE_X = 404;
// Au pied du poste du reviewer, dont les refus la remplissent.
const CORBEILLE_X = 634;
const ABSCISSES_DU_MUR: AbscissesDuMur = {
  fenetres: FENETRES_X,
  plafonniers: PLAFONNIERS_X,
  horloge: HORLOGE_X,
  cadre: CADRE_X,
  interrupteur: INTERRUPTEUR_X,
};
/** Le tableau blanc, un peu plus grand que le reste : il tient la moitié de la hauteur du mur. */
const TABLEAU_RELATIF = 1.15;

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
  /** Ouvre le projet dans l'onglet Tickets : la porte en devient un bouton. Sans lui, elle reste un meuble. */
  onOpenProject?: () => void;
}

/** La porte dépasse les agents d'une tête : à l'échelle commune, elle était plus petite qu'eux (ticket-622). */
const ECHELLE_DE_LA_PORTE = 1.5;

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
  onOpenProject,
}: FondDeLaPieceProps) {
  const moment = dayMoment(maintenant);
  // Le dessus du meuble, une fois agrandi : la pile s'y pose, à droite de l'imprimante.
  const dessusDuMeuble = HAUTEUR_DU_MEUBLE * useEchelleDesSprites();
  const ciels = cielDesFenetres(projet, FENETRES_X.length, maintenant);
  return (
    <div
      className="relative h-36 border-b-4 border-(--sprite-plinthe) bg-(--sprite-mur)"
      data-fond="piece"
      data-mur="piece"
    >
      <MurLumineux
        moment={moment}
        ciels={ciels}
        allume={allume}
        onBasculer={onBasculerLumiere}
        maintenant={maintenant}
        salle={projet}
        abscisses={ABSCISSES_DU_MUR}
      />
      <Pose x={ETAGERE_X} bas="top-12">
        <Agrandi>
          <Etagere />
        </Agrandi>
      </Pose>
      <Pose x={CORBEILLE_X}>
        <Agrandi>
          <Corbeille boules={boulesDeLaCorbeille(etat)} />
        </Agrandi>
      </Pose>
      <Pose x={TABLEAU_X} bas="top-5">
        <TableauDesCriteres
          projet={projet}
          etat={etat}
          relatif={TABLEAU_RELATIF}
        />
      </Pose>
      <Pose x={BIBLIOTHEQUE_X}>
        <Agrandi>
          <Bibliotheque />
        </Agrandi>
      </Pose>
      <Pose x={FICUS_X}>
        <Agrandi>
          <Plante espece="ficus" />
        </Agrandi>
      </Pose>
      <Pose x={IMPRIMANTE_X}>
        <span className="relative block">
          <Agrandi>
            <Imprimante />
          </Agrandi>
          <span className="absolute right-1" style={{ bottom: dessusDuMeuble }}>
            <Dossiers
              projet={projet}
              runId={runId}
              etat={etat}
              onActiver={onOpenProject}
            />
          </span>
        </span>
      </Pose>
      <Pose x={MACHINE_X}>
        <Agrandi>
          <MachineACafe />
        </Agrandi>
      </Pose>
      {machineEnService && (
        <Pose x={MACHINE_X} bas="bottom-18">
          <Vapeur />
        </Pose>
      )}
      <Pose x={BAIE_X}>
        <BaieDeServeurs services={services} />
      </Pose>
      <Pose x={CACTUS_X}>
        <Agrandi>
          <Plante espece="cactus" />
        </Agrandi>
      </Pose>
      <Pose x={BOITE_X}>
        <BoiteAuxLettres projet={projet} etat={etat} />
      </Pose>
      <Pose x={PORTE_X}>
        {onOpenProject ? (
          <button
            type="button"
            aria-label={`Ouvrir le projet ${projet}`}
            onClick={onOpenProject}
            className="block cursor-pointer rounded-sm focus-visible:outline-2 focus-visible:outline-violet-500"
          >
            <Agrandi relatif={ECHELLE_DE_LA_PORTE}>
              <Porte />
            </Agrandi>
          </button>
        ) : (
          <Agrandi relatif={ECHELLE_DE_LA_PORTE}>
            <Porte />
          </Agrandi>
        )}
      </Pose>
    </div>
  );
}
