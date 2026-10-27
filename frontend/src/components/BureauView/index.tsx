import { useState } from "react";
import type { StreamState } from "../../hooks/streamState";
import { useAlerteSonore } from "../../hooks/useAlerteSonore";
import { useSanteDuBureau } from "../../hooks/useSanteDuBureau";
import { contenuAToi } from "../../lib/bureau/aToi";
import { modeCompact } from "../../lib/bureau/modeCompact";
import type { RunActif } from "../../types/api";
import AuRepos from "./AuRepos";
import ColonneAToi from "./ColonneAToi";
import type { ReglageSon } from "./ColonneAToi";
import Compact from "./Compact";
import PanneauAgentChoisi from "./PanneauAgentChoisi";
import type { AgentChoisi } from "./PanneauAgentChoisi";
import Piece from "./Piece";
import SallesCommunes from "./SallesCommunes";
import TableauDuJour from "./TableauDuJour";

export interface ProjetDuBureau {
  nom: string;
  etat: StreamState;
  /** Le run vivant du projet, quand on le connaît. */
  runId?: string | null;
  /** Le run lui-même, pour le chrono, le fil et le rangement. */
  run?: RunActif;
}

interface BureauViewProps {
  projets: readonly ProjetDuBureau[];
  /** Compteur d'événements de service de la supervision (`signalServices`). */
  signalServices?: number;
  /** Le canal de la supervision : la réponse d'une question passe par `{ type: "answer" }`. */
  envoyer: (runId: string, payload: Record<string, string>) => void;
  /** Le réglage « Son » de la question (ticket-554), tenu par la cloche : le Bureau n'en a pas un à lui. */
  son: ReglageSon;
  /** Les projets sans run : ils ne comptent pas pour le seuil, et ne se dessinent qu'en compact. */
  auRepos?: readonly string[];
  /** Ouvre le fil d'un run (ticket-567). */
  onOuvrir?: (runId: string) => void;
  /** Range un run clos (ticket-567). */
  onRanger?: (runId: string) => void;
}

/**
 * Les pièces des projets qui ont un run, ou leurs rangées au-delà du seuil de
 * `modeCompact`. L'horloge se monte ici, une seule fois pour toute la vue.
 */
export default function BureauView({
  projets,
  signalServices = 0,
  envoyer,
  son,
  auRepos = [],
  onOuvrir,
  onRanger,
}: BureauViewProps) {
  const maintenant = useSanteDuBureau();
  // L'agent choisi : seul le couple est retenu, ses lignes se relisent à chaque rendu.
  const [choix, setChoix] = useState<AgentChoisi | null>(null);
  const projetChoisi = projets.find((p) => p.nom === choix?.projet);
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
        <SallesCommunes projets={projets} maintenant={maintenant} />
        <div
          className={compact ? "flex flex-col gap-2" : "flex flex-col gap-3.5"}
          data-mode={compact ? "compact" : "pieces"}
        >
          {projets.map(({ nom, etat, runId = null, run }) =>
            compact ? (
              <Compact
                key={nom}
                projet={nom}
                etat={etat}
                maintenant={maintenant}
                run={run}
                onOuvrir={onOuvrir}
                onRanger={onRanger}
              />
            ) : (
              <Piece
                key={nom}
                projet={nom}
                etat={etat}
                maintenant={maintenant}
                runId={runId}
                signalServices={signalServices}
                run={run}
                onOuvrir={onOuvrir}
                onRanger={onRanger}
                onChoisir={(projet, poste) => setChoix({ projet, poste })}
              />
            ),
          )}
          {compact && auRepos.map((nom) => <AuRepos key={nom} projet={nom} />)}
        </div>
      </div>
      <div className="flex w-72 shrink-0 flex-col gap-3.5">
        <ColonneAToi
          contenu={aToi}
          maintenant={maintenant}
          onAnswer={(runId, text) => envoyer(runId, { type: "answer", text })}
          son={son}
        />
        <PanneauAgentChoisi
          choix={choix}
          etat={projetChoisi?.etat}
          run={projetChoisi?.run}
          maintenant={maintenant}
          onOuvrir={onOuvrir}
        />
      </div>
    </div>
  );
}
