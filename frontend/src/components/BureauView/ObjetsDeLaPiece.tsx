import type { StreamState } from "../../hooks/streamState";
import BaieDeServeurs from "./BaieDeServeurs";
import BoiteAuxLettres from "./BoiteAuxLettres";
import Dossiers from "./Dossiers";

interface ObjetsDeLaPieceProps {
  projet: string;
  etat: StreamState;
  /** Identifiant du run vivant, `null` quand on ne le connaît pas : pas de pile. */
  runId: string | null;
  signalServices: number;
}

/**
 * Les trois objets de la pièce : la pile de dossiers, la boîte aux lettres et la baie,
 * chacun dans sa colonne. Une colonne dont l'objet est absent reste vide : la boîte
 * ne change pas de place.
 */
export default function ObjetsDeLaPiece({ projet, etat, runId, signalServices }: ObjetsDeLaPieceProps) {
  return (
    <div className="grid grid-cols-3 items-end gap-2 border-t border-zinc-800 px-3 py-2">
      <div className="flex justify-center">
        <Dossiers projet={projet} runId={runId} etat={etat} />
      </div>
      <div className="flex justify-center">
        <BoiteAuxLettres projet={projet} etat={etat} />
      </div>
      <div className="flex justify-center">
        <BaieDeServeurs projet={projet} signalServices={signalServices} />
      </div>
    </div>
  );
}
