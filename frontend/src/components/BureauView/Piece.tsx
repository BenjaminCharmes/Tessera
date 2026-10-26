import Pastille from "../../design/bureau/Pastille";
import type { StreamState } from "../../hooks/streamState";
import { contourDeLaPiece } from "../../lib/bureau/contourDeLaPiece";
import type { ContourDeLaPiece } from "../../lib/bureau/contourDeLaPiece";
import { postesDuRun } from "../../lib/bureau/postesDuRun";
import type { PosteId } from "../../lib/bureau/postesDuRun";
import { enEtapeSilencieuse, santeAgent } from "../../lib/santeAgent";
import type { RunActif } from "../../types/api";
import ActionsDuRun from "./ActionsDuRun";
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

  return (
    <section
      aria-label={projet}
      data-contour={contour}
      className={`overflow-hidden rounded-lg border bg-zinc-900 ${CONTOURS[contour]}`}
    >
      <div className="flex items-center justify-between gap-2 border-b border-zinc-800 px-3 py-2">
        <h3 className="truncate text-corps font-semibold text-zinc-200">{projet}</h3>
        {run && <ActionsDuRun run={run} etat={etat} onOuvrir={onOuvrir} onRanger={onRanger} />}
      </div>
      <div className="grid grid-cols-5 items-end gap-1 border-b-8 border-zinc-800 px-2.5">
        {postes.map((p) => (
          <PosteDeTravail
            key={p.poste}
            poste={p}
            sante={sante}
            onChoisir={onChoisir && ((poste) => onChoisir(projet, poste))}
          />
        ))}
      </div>
      <div className="flex min-h-9 items-center px-3 py-2">{enCours && <Pastille sante={sante} />}</div>
      <ObjetsDeLaPiece projet={projet} etat={etat} runId={runId} signalServices={signalServices} />
    </section>
  );
}
