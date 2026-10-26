import type { StreamState } from "../../hooks/streamState";
import { useSanteDuBureau } from "../../hooks/useSanteDuBureau";
import { modeCompact } from "../../lib/bureau/modeCompact";
import Compact from "./Compact";
import Piece from "./Piece";
import TableauDuJour from "./TableauDuJour";

export interface ProjetDuBureau {
  nom: string;
  etat: StreamState;
  /** Le run vivant du projet, quand on le connaît. */
  runId?: string | null;
}

interface BureauViewProps {
  projets: readonly ProjetDuBureau[];
  /** Compteur d'événements de service de la supervision (`signalServices`). */
  signalServices?: number;
}

/**
 * Les pièces des projets qui ont un run, ou leurs rangées au-delà du seuil de
 * `modeCompact`. L'horloge se monte ici, une seule fois pour toute la vue.
 */
export default function BureauView({ projets, signalServices = 0 }: BureauViewProps) {
  const maintenant = useSanteDuBureau();
  const compact = modeCompact(projets.length);

  // Un run qui se clôt fait relire le tableau. Un compte et non un événement :
  // la vue ne reçoit que des états, et `runClosed` y est posé par `run_closed`.
  const runsClos = projets.filter((p) => p.etat.runClosed).length;

  return (
    <div className="flex flex-col gap-3.5">
      <TableauDuJour maintenant={maintenant} signalRunsClos={runsClos} />
      <div
        className={compact ? "flex flex-col gap-2" : "grid grid-cols-2 gap-3.5"}
        data-mode={compact ? "compact" : "pieces"}
      >
        {projets.map(({ nom, etat, runId = null }) =>
          compact ? (
            <Compact key={nom} projet={nom} etat={etat} maintenant={maintenant} />
          ) : (
            <Piece
              key={nom}
              projet={nom}
              etat={etat}
              maintenant={maintenant}
              runId={runId}
              signalServices={signalServices}
            />
          ),
        )}
      </div>
    </div>
  );
}
