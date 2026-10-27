import Pastille from "../../design/bureau/Pastille";
import Plante from "../../design/bureau/Plante";
import type { StreamState } from "../../hooks/streamState";
import { useActivites } from "../../hooks/useActivites";
import { machineEnService, placerLesAgents, postesFaits } from "../../lib/bureau/activites";
import type { Hasard } from "../../lib/bureau/activites";
import { contourDeLaPiece } from "../../lib/bureau/contourDeLaPiece";
import type { ContourDeLaPiece } from "../../lib/bureau/contourDeLaPiece";
import StatusPill from "../../design/ui/StatusPill";
import { libelleDeSuite } from "../../lib/bureau/etapeDeSuite";
import { postesDuRun } from "../../lib/bureau/postesDuRun";
import { postesAbsents } from "../../lib/bureau/sallesCommunes";
import type { PosteId } from "../../lib/bureau/postesDuRun";
import { enEtapeSilencieuse, santeAgent } from "../../lib/santeAgent";
import type { RunActif } from "../../types/api";
import ActionsDuRun from "./ActionsDuRun";
import AgentsDeLaPiece from "./AgentsDeLaPiece";
import FondDeLaPiece from "./FondDeLaPiece";
import ObjetsDeLaPiece from "./ObjetsDeLaPiece";
import PosteDeTravail from "./PosteDeTravail";

interface PieceProps {
  projet: string;
  etat: StreamState;
  /** L'horloge unique de la vue : la pièce n'ouvre aucun minuteur. */
  maintenant: number;
  /** Le run vivant du projet : sans lui, pas de pile de dossiers. */
  runId?: string | null;
  /** Compteur d'événements de service, relu par la baie. */
  signalServices?: number;
  /** Le run du projet : sans lui, ni chrono ni accès au fil. */
  run?: RunActif;
  onOuvrir?: (runId: string) => void;
  onRanger?: (runId: string) => void;
  /** Choisit l'agent d'un poste occupé : le panneau « Agent choisi » le lit (ticket-582). */
  onChoisir?: (projet: string, poste: PosteId) => void;
  /** Le tirage des activités de pause : `Math.random` par défaut, une suite fixe dans les tests. */
  hasard?: Hasard;
}

const CONTOURS: Record<ContourDeLaPiece, string> = {
  neutre: "border-zinc-800",
  vert: "border-green-900",
  rouge: "border-red-900",
  amber: "border-amber-900",
};

/** La pièce d'un projet : cinq postes dans l'ordre du pipeline, contour selon l'issue ou la santé. */
export default function Piece({
  projet,
  etat,
  maintenant,
  runId = null,
  signalServices = 0,
  run,
  onOuvrir,
  onRanger,
  onChoisir,
  hasard,
}: PieceProps) {
  const postes = postesDuRun(etat);
  const sante = santeAgent(
    etat.dernierEvenementA,
    maintenant,
    etat.pendingQuestion,
    etat.attenteExterieure !== null,
    enEtapeSilencieuse(etat),
  );
  const contour = contourDeLaPiece(etat, sante);
  const enCours = postes.some((p) => p.etat === "occupe");
  // Documentation et livraison n'ont pas de poste : la pastille du pied les dit (ticket-585).
  const suite = libelleDeSuite(etat.etape);
  // Aucun événement de ticket : pas de run, donc personne à dessiner.
  const auRepos = etat.ticketEvents.length === 0;
  // Run clos : les cinq agents sont partis par la porte. Sans run, personne à placer.
  const clos = !auRepos && etat.runClosed;
  const faits = auRepos ? [] : postesFaits(postes);
  const activites = useActivites(faits, maintenant, hasard);
  // Un agent chez le directeur ou aux RH n'est plus à sa place : il ne se dessine qu'à un endroit.
  const absents = postesAbsents(etat, maintenant);
  const agents = placerLesAgents(faits, activites, clos).map((a) =>
    absents.includes(a.poste) ? { ...a, activite: null, parti: true } : a,
  );

  return (
    <section
      aria-label={projet}
      data-contour={contour}
      className={`overflow-hidden rounded-lg border bg-zinc-900 ${CONTOURS[contour]}`}
    >
      <div className="flex items-center justify-between gap-2 border-b border-zinc-800 px-3 py-[5px]">
        <h3 className="truncate text-corps font-semibold text-zinc-200">{projet}</h3>
        {run && <ActionsDuRun run={run} etat={etat} onOuvrir={onOuvrir} onRanger={onRanger} />}
      </div>
      <div data-sol="lames" className="sol-lames">
        {/* Sol de 800 px, celui de la maquette : plus étroite, la pièce défile. */}
        <div className="overflow-x-auto">
          <div className="relative w-200">
            <FondDeLaPiece machineEnService={machineEnService(agents)} />
            <div className="grid h-33 grid-cols-5 items-end gap-1 border-b-8 border-zinc-800 px-2.5">
              {postes.map((p) => (
                <PosteDeTravail
                  key={p.poste}
                  projet={projet}
                  poste={p}
                  sante={sante}
                  auRepos={auRepos}
                  parti={clos}
                  absent={absents.includes(p.poste)}
                  onChoisir={onChoisir && ((poste) => onChoisir(projet, poste))}
                />
              ))}
            </div>
            <AgentsDeLaPiece projet={projet} agents={agents} />
          </div>
        </div>
        <div className="flex min-h-9 items-end justify-between px-3 py-2">
          <div className="flex min-h-5 items-center">
            {enCours && <Pastille sante={sante} />}
            {!enCours && suite && <StatusPill etat="en-cours" libelle={suite} />}
          </div>
          <Plante />
        </div>
        <ObjetsDeLaPiece projet={projet} etat={etat} runId={runId} signalServices={signalServices} />
      </div>
    </section>
  );
}
