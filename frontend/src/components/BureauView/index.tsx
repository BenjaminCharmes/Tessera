import type { StreamState } from "../../hooks/streamState";
import { useAlerteSonore } from "../../hooks/useAlerteSonore";
import { useSanteDuBureau } from "../../hooks/useSanteDuBureau";
import { contenuAToi } from "../../lib/bureau/aToi";
import { modeCompact } from "../../lib/bureau/modeCompact";
import ColonneAToi from "./ColonneAToi";
import type { ReglageSon } from "./ColonneAToi";
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
  /** Le canal de la supervision : la réponse d'une question passe par `{ type: "answer" }`. */
  envoyer: (runId: string, payload: Record<string, string>) => void;
  /** Le réglage « Son » de la question (ticket-554), tenu par la cloche : le Bureau n'en a pas un à lui. */
  son: ReglageSon;
}

/**
 * Les pièces des projets qui ont un run, ou leurs rangées au-delà du seuil de
 * `modeCompact`. L'horloge se monte ici, une seule fois pour toute la vue.
 */
export default function BureauView({ projets, signalServices = 0, envoyer, son }: BureauViewProps) {
  const maintenant = useSanteDuBureau();
  const compact = modeCompact(projets.length);

  // Un run qui se clôt fait relire le tableau. Un compte et non un événement :
  // la vue ne reçoit que des états, et `runClosed` y est posé par `run_closed`.
  const runsClos = projets.filter((p) => p.etat.runClosed).length;

  const aToi = contenuAToi(projets, maintenant);
  useAlerteSonore(
    aToi.questions.map((q) => q.projet),
    son.actif,
  );

  return (
    <div className="flex items-start gap-3.5">
      <div className="flex min-w-0 flex-1 flex-col gap-3.5">
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
      <div className="w-72 shrink-0">
        <ColonneAToi
          contenu={aToi}
          maintenant={maintenant}
          onAnswer={(runId, text) => envoyer(runId, { type: "answer", text })}
          son={son}
        />
      </div>
    </div>
  );
}
