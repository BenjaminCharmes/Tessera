import Pastille from "../../design/bureau/Pastille";
import type { StreamState } from "../../hooks/streamState";
import { contourDeLaPiece } from "../../lib/bureau/contourDeLaPiece";
import type { ContourDeLaPiece } from "../../lib/bureau/contourDeLaPiece";
import { postesDuRun } from "../../lib/bureau/postesDuRun";
import { santeAgent } from "../../lib/santeAgent";
import PosteDeTravail from "./PosteDeTravail";

interface PieceProps {
  projet: string;
  etat: StreamState;
  /** L'horloge unique de la vue : la pièce n'ouvre aucun minuteur. */
  maintenant: number;
}

const CONTOURS: Record<ContourDeLaPiece, string> = {
  neutre: "border-zinc-800",
  vert: "border-green-900",
  rouge: "border-red-900",
  amber: "border-amber-900",
};

/** La pièce d'un projet : cinq postes dans l'ordre du pipeline, contour selon l'issue ou la santé. */
export default function Piece({ projet, etat, maintenant }: PieceProps) {
  const postes = postesDuRun(etat);
  const sante = santeAgent(etat.dernierEvenementA, maintenant, etat.pendingQuestion);
  const contour = contourDeLaPiece(etat, sante);
  const enCours = postes.some((p) => p.etat === "occupe");

  return (
    <section
      aria-label={projet}
      data-contour={contour}
      className={`overflow-hidden rounded-lg border bg-zinc-900 ${CONTOURS[contour]}`}
    >
      <h3 className="border-b border-zinc-800 px-3 py-2 text-corps font-semibold text-zinc-200">
        {projet}
      </h3>
      <div className="grid grid-cols-5 items-end gap-1 border-b-8 border-zinc-800 px-2.5">
        {postes.map((p) => (
          <PosteDeTravail key={p.poste} poste={p} sante={sante} />
        ))}
      </div>
      <div className="flex min-h-9 items-center px-3 py-2">{enCours && <Pastille sante={sante} />}</div>
    </section>
  );
}
