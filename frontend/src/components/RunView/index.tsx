import { useState } from "react";
import RegionTitle from "../../design/RegionTitle";
import { BAND } from "../../design/layout";
import {
  IconCheck,
  IconChevronDown,
  IconChevronRight,
} from "../../design/icons";
import TokenStream from "../AgentPanel/TokenStream";
import VerdictBanner from "../AgentPanel/VerdictBanner";
import PipelineSummary from "../AgentPanel/PipelineSummary";
import { resumeDuCout } from "../../lib/budget";
import type { UseRunActifResult, PassageAgent } from "../../hooks/streamState";

/**
 * Ce que le run est en train de faire, au centre de l'écran (ticket-075).
 *
 * Le panneau est un fil chronologique (ticket-222) : Codeur (tour 1) →
 * Reviewer (tour 1) → Codeur (tour 2) → … Chaque passage est une entrée
 * ajoutée dans l'ordre. Les passages terminés sont repliés ; l'entrée en
 * cours reste dépliée.
 */
interface RunViewProps {
  stream: UseRunActifResult;
}

/** Résumé court affiché dans l'en-tête d'une entrée repliée. */
function resumePassage(entry: PassageAgent): string {
  if (entry.agent === "reviewer") {
    if (!entry.content) return "";
    const approved =
      entry.content.includes("APPROVED") &&
      !entry.content.includes("CHANGES_REQUESTED");
    return approved ? "APPROVED" : "CHANGES_REQUESTED";
  }
  // Codeur : première ligne non vide du compte rendu.
  return entry.content.split("\n").find((l) => l.trim()) ?? "";
}

interface EntreePipelineProps {
  entry: PassageAgent;
  /** Vraie si c'est la dernière entrée du fil (toujours dépliée). */
  isLast: boolean;
}

/**
 * Un passage d'agent dans le fil — repliable quand terminé et pas le dernier.
 */
function EntreePipeline({ entry, isLast }: EntreePipelineProps) {
  const [expanded, setExpanded] = useState(false);

  // L'entrée en cours reste dépliée ; les autres se replient par défaut.
  const ouvert = isLast || expanded;
  const peutBasculer = entry.isDone && !isLast;

  const approved =
    entry.agent === "reviewer" &&
    entry.content.includes("APPROVED") &&
    !entry.content.includes("CHANGES_REQUESTED");

  const resume = resumePassage(entry);

  return (
    <div
      className="mx-3 mb-3 rounded-sm border border-zinc-700 overflow-hidden"
      data-testid="entree-pipeline"
    >
      <button
        type="button"
        disabled={!peutBasculer}
        onClick={() => peutBasculer && setExpanded((v) => !v)}
        aria-expanded={ouvert}
        className="flex w-full items-center gap-2 px-3 py-2 bg-zinc-800 text-xs font-semibold text-zinc-300 text-left disabled:cursor-default"
      >
        <span>{entry.agent.toUpperCase()}</span>

        {/* Entrée terminée et repliable : résumé + chevron. */}
        {peutBasculer && (
          <span
            className={`ml-auto flex items-center gap-1 font-normal ${
              approved ? "text-green-400" : "text-zinc-400"
            }`}
          >
            {resume && <span className="max-w-48 truncate">{resume}</span>}
            {ouvert ? <IconChevronDown size={12} /> : <IconChevronRight size={12} />}
          </span>
        )}

        {/* Entrée en cours : points de chargement. */}
        {isLast && !entry.isDone && (
          <span className="ml-auto flex gap-0.5">
            {[0, 150, 300].map((delay) => (
              <span
                key={delay}
                className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-bounce"
                style={{ animationDelay: `${delay}ms` }}
              />
            ))}
          </span>
        )}

        {/* Dernière entrée, terminée. */}
        {isLast && entry.isDone && (
          <span className="ml-auto flex items-center gap-1 font-normal text-green-400">
            <IconCheck size={12} /> terminé
          </span>
        )}
      </button>

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
            <VerdictBanner content={entry.content} />
          )}
          {!entry.tokens && !entry.content && (
            <div className="text-zinc-600 text-xs italic">Génération…</div>
          )}
        </div>
      )}
    </div>
  );
}

export default function RunView({ stream }: RunViewProps) {
  const { entries, currentRound, lastResult, queue } = stream;

  return (
    <div className="flex h-full flex-col bg-zinc-900">
      <div className={`${BAND} justify-between gap-3 border-b border-zinc-700 px-4`}>
        <RegionTitle>Run en cours</RegionTitle>
        <div className="flex items-center gap-3 text-mini text-zinc-400">
          {queue && (
            <span className="text-zinc-300">
              File : {queue.index}/{queue.total}
            </span>
          )}
          {stream.ticketId && (
            <span className="font-mono text-zinc-500">{stream.ticketId}</span>
          )}
          {currentRound > 0 && <span>Tour {currentRound}</span>}
          {(stream.coutUsd > 0 || stream.outils > 0) && (
            <span data-testid="cout-du-run">
              {resumeDuCout(stream.coutUsd, stream.appels, stream.outils)}
            </span>
          )}
          {stream.currentAgent && (
            <span className="text-blue-300">{stream.currentAgent.toUpperCase()}</span>
          )}
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto py-3">
        {entries.length === 0 && (
          <p className="px-4 text-xs text-zinc-500">
            Le run démarre : la branche se crée et le premier agent se prépare.
          </p>
        )}

        {entries.map((entry, idx) => (
          <EntreePipeline
            key={entry.id}
            entry={entry}
            isLast={idx === entries.length - 1}
          />
        ))}

        {lastResult && (
          <PipelineSummary result={lastResult} runClosed={stream.runClosed} />
        )}
      </div>
    </div>
  );
}
