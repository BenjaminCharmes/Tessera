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

/** Les trois objets de la pièce : la pile de dossiers, la boîte aux lettres et la baie. */
export default function ObjetsDeLaPiece({ projet, etat, runId, signalServices }: ObjetsDeLaPieceProps) {
  return (
    <div className="flex items-end gap-4 border-t border-zinc-800 px-3 py-2">
      <Dossiers projet={projet} runId={runId} etat={etat} />
      <BoiteAuxLettres projet={projet} etat={etat} />
      <BaieDeServeurs projet={projet} signalServices={signalServices} />
    </div>
  );
}
