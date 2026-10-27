import Button from "../../design/ui/Button";
import StatusPill from "../../design/ui/StatusPill";
import type { StreamState } from "../../hooks/streamState";
import type { RunActif } from "../../types/api";
import Chrono from "../SupervisionView/Chrono";
import { clotureDuRun, etatAffiche, issueAffichee } from "../SupervisionView/etatDuRun";
import { issueDuRun } from "../SupervisionView/issueDuRun";

export interface ActionsDuRunProps {
  run: RunActif;
  etat: StreamState;
  /** Ouvre le fil du run ; sans lui, pas de bouton. */
  onOuvrir?: (runId: string) => void;
  /** Range un run clos ; sans lui, ou tant que le run court, pas de bouton. */
  onRanger?: (runId: string) => void;
}

/**
 * Ce que la Liste dit d'un run et que le Bureau doit dire aussi : le chrono,
 * l'état, l'issue une fois clos, puis l'accès au fil et le rangement. Les mots
 * viennent des mêmes fonctions que `RunCard` (ADR-034).
 */
export default function ActionsDuRun({ run, etat, onOuvrir, onRanger }: ActionsDuRunProps) {
  const issue = issueDuRun(etat);
  const issueDite = issueAffichee(issue);
  const nom = run.ticket_id ?? run.mode;

  return (
    <div className="flex shrink-0 items-center gap-2" data-issue={issue}>
      <span className="text-micro tabular-nums text-zinc-500">
        <Chrono depuis={run.demarre_a} termineA={clotureDuRun(etat)} />
      </span>
      <StatusPill {...etatAffiche(etat)} />
      {issueDite && <StatusPill {...issueDite} />}
      {onOuvrir && (
        <Button taille="pastille" aria-label={`Ouvrir le fil de ${nom}`} onClick={() => onOuvrir(run.run_id)}>
          Fil
        </Button>
      )}
      {etat.runClosed && onRanger && (
        <Button taille="pastille" aria-label={`Ranger ${nom}`} onClick={() => onRanger(run.run_id)}>
          Ranger
        </Button>
      )}
    </div>
  );
}
