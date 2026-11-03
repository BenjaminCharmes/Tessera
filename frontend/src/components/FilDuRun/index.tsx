import { useState } from "react";
import { formatDurationMs } from "../../lib/format";
import TokenStream from "../AgentPanel/TokenStream";
import VerdictBanner from "../AgentPanel/VerdictBanner";
import { verdictDuReviewer } from "./verdict";
import EnteteVerdict from "./EnteteVerdict";
import EntreeSecuriteView from "./EntreeSecuriteView";
import EntreeTesteurView from "./EntreeTesteurView";
import EntreeValidateurView from "./EntreeValidateurView";
import type { EntreeFil, PassageAgent } from "../../hooks/streamState";

// ---------------------------------------------------------------------------
// EntreePipeline — passage d'un agent (codeur ou reviewer)
// ---------------------------------------------------------------------------

interface EntreePipelineProps {
  entry: PassageAgent;
  isLast: boolean;
}

/**
 * Un passage d'agent dans le fil — repliable quand terminé et pas le dernier.
 */
function EntreePipeline({ entry, isLast }: EntreePipelineProps) {
  const [expanded, setExpanded] = useState(false);
  const ouvert = isLast || expanded;
  const peutBasculer = entry.isDone && !isLast;
  const loading = isLast && !entry.isDone;

  const approved =
    entry.agent === "reviewer"
      ? verdictDuReviewer(entry) === "APPROVED"
      : true;

  let verdictText: string;
  if (entry.agent === "reviewer") {
    verdictText = approved ? "APPROVED" : "CHANGES_REQUESTED";
  } else if (peutBasculer && entry.duration_ms !== undefined) {
    verdictText = `terminé · ${formatDurationMs(entry.duration_ms, "fil")}`;
  } else {
    verdictText = "terminé";
  }

  return (
    <div
      className="mx-3 mb-3 rounded-sm border border-zinc-700 overflow-hidden"
      data-testid="entree-pipeline"
    >
      <EnteteVerdict
        label={entry.agent.toUpperCase()}
        approved={approved}
        verdictText={verdictText}
        loading={loading}
        peutBasculer={peutBasculer}
        ouvert={ouvert}
        onToggle={() => setExpanded((v) => !v)}
      />

      {ouvert && (
        <div className="p-3">
          {entry.agent === "codeur" && !entry.isDone && entry.tokens && (
            <TokenStream tokens={entry.tokens} isActive={isLast} />
          )}
          {entry.agent === "codeur" && entry.isDone && entry.content && (
            <pre className="max-h-64 overflow-auto whitespace-pre-wrap wrap-break-word rounded-sm bg-zinc-950/60 p-2 font-mono text-mini text-zinc-300">
              {entry.content}
            </pre>
          )}
          {entry.agent === "reviewer" && entry.content && (
            <VerdictBanner content={entry.content} verdict={entry.verdict} />
          )}
          {!entry.tokens && !entry.content && (
            <div className="text-zinc-600 text-xs italic">Génération…</div>
          )}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// FilDuRun — export principal
// ---------------------------------------------------------------------------

interface FilDuRunProps {
  entries: EntreeFil[];
}

/**
 * Fil chronologique d'un run : agents, sécurité et validateur dans l'ordre.
 *
 * Partagé entre RunView (vue centrée du run) et AgentPanel (panneau latéral).
 * Les entrées terminées et non-dernières sont repliées ; la dernière reste
 * dépliée. Un observateur arrivé après le début n'a aucune entrée : le
 * composant parent gère ce repli avec `blocsDuPanneau` (ticket-257).
 */
export default function FilDuRun({ entries }: FilDuRunProps) {
  return (
    <>
      {entries.map((entry, idx) => {
        const isLast = idx === entries.length - 1;
        if (entry.genre === "securite") {
          return (
            <EntreeSecuriteView key={entry.id} entry={entry} isLast={isLast} />
          );
        }
        if (entry.genre === "validateur") {
          return (
            <EntreeValidateurView
              key={entry.id}
              entry={entry}
              isLast={isLast}
            />
          );
        }
        if (entry.genre === "testeur") {
          return (
            <EntreeTesteurView key={entry.id} entry={entry} isLast={isLast} />
          );
        }
        return <EntreePipeline key={entry.id} entry={entry} isLast={isLast} />;
      })}
    </>
  );
}
