import { BAND } from "../../design/layout";
import RegionTitle from "../../design/RegionTitle";
import { IconCross } from "../../design/icons";
import RoundBadge from "./RoundBadge";
import { resumeDuCout } from "../../lib/budget";
import QuotaBadge from "./QuotaBadge";
import AgentDialogue from "./AgentDialogue";
import TicketActivity from "./TicketActivity";
import AgentBlock from "./AgentBlock";
import { blocsDuPanneau } from "./blocsDuPanneau";
import PipelineSummary from "./PipelineSummary";
import StageStrip from "./StageStrip";
import FilDuRun from "../FilDuRun";
import type { Project, Ticket, PipelineReglages } from "../../types/api";
import type { UseRunActifResult } from "../../hooks/streamState";

interface AgentPanelProps {
  project: Project | null;
  stream: UseRunActifResult;
  /** Ticket sélectionné, pour afficher ce qu'il a produit (ticket-064). */
  activeTicket?: Ticket | null;
  /** Configuration du pipeline pour la frise d'étapes (ticket-256). */
  reglages?: Pick<PipelineReglages, "securite_enabled" | "validateur_enabled"> | null;
}

export default function AgentPanel({
  project,
  stream,
  activeTicket = null,
  reglages = null,
}: AgentPanelProps) {
  const {
    status,
    ticketId,
    ticketTitre,
    currentAgent,
    currentRound,
    coutUsd,
    appels,
    outils,
    currentTokens,
    lastResult,
    errorMessage,
    events,
    etape,
    etapesEnCours,
    quota,
    pendingQuestion,
    questionExpireA,
    runClosed,
    entries,
    answer,
    interject,
    stop,
    clear,
  } = stream;

  // L'état décide, les événements enrichissent : un observateur arrivé après
  // le début n'a aucun événement, et le panneau restait vide pendant qu'un run
  // travaillait (ticket-182).
  const { coderStarted, coderDone, reviewerStarted } = blocsDuPanneau(
    events,
    currentAgent,
  );

  const reviewerContent =
    events
      .filter((e) => e.type === "agent_done" && e.agent === "reviewer")
      .map((e) =>
        typeof e.data["content"] === "string" ? e.data["content"] : "",
      )
      .at(-1) ?? "";

  // Compte rendu complet du codeur : rejoué après reconnexion (ticket-216, ADR-041).
  const codeurDoneContent =
    events
      .filter((e) => e.type === "agent_done" && e.agent === "codeur")
      .map((e) =>
        typeof e.data["content"] === "string" ? e.data["content"] : "",
      )
      .at(-1) ?? "";

  const startTs = events.find((e) => e.type === "agent_started")?.timestamp;
  const endTs = events.find((e) => e.type === "pipeline_done")?.timestamp;
  const durationMs =
    startTs && endTs
      ? new Date(endTs).getTime() - new Date(startTs).getTime()
      : undefined;

  // Résultat de la livraison, affiché dans PipelineSummary après run_closed (ticket-279).
  const livraisonEvent = events.find((e) => e.type === "livraison_done");
  const livraisonData = livraisonEvent
    ? {
        pr_number:
          typeof livraisonEvent.data["pr_number"] === "number"
            ? livraisonEvent.data["pr_number"]
            : undefined,
        merged: livraisonEvent.data["merged"] === true,
        arret:
          typeof livraisonEvent.data["arret"] === "string"
            ? livraisonEvent.data["arret"]
            : undefined,
      }
    : null;

  return (
    <div className="flex h-full flex-col bg-zinc-900">
      {/* Header */}
      <div className={`${BAND} justify-between border-b border-zinc-700 px-4`}>
        <RegionTitle>
          Agents
          {ticketId && (
            <span
              className="ml-2 min-w-0 truncate font-normal normal-case text-zinc-600"
              title={ticketTitre ?? undefined}
            >
              — {ticketId}
              {ticketTitre ? ` · ${ticketTitre}` : ""}
            </span>
          )}
        </RegionTitle>
        <div className="flex items-center gap-2">
          <QuotaBadge quota={quota} />
          {project && !ticketId && (
            <span className="text-xs text-zinc-600">{project.name}</span>
          )}
          {(runClosed || status === "error") && (
            <button
              onClick={clear}
              title="Effacer le run"
              aria-label="Effacer le run"
              className="text-zinc-600 hover:text-zinc-300 transition-colors text-sm"
            >
              <IconCross size={14} />
            </button>
          )}
        </div>
      </div>

      {/* Body */}
      <div className="flex-1 overflow-y-auto">
        {status === "idle" && (
          <div className="flex items-center justify-center h-full text-zinc-700 text-xs italic">
            {project
              ? "Lance un ticket pour commencer"
              : "Sélectionne un projet"}
          </div>
        )}

        {status === "connecting" && (
          <div className="flex items-center justify-center h-full text-zinc-500 text-xs">
            <span className="animate-pulse">Connexion…</span>
          </div>
        )}

        {(status === "running" || status === "done") && (
          <>
            <StageStrip etape={etape} etapesEnCours={etapesEnCours} events={events} reglages={reglages} />
            {currentRound > 0 && <RoundBadge current={currentRound} />}
            {(coutUsd > 0 || outils > 0) && (
              <p className="px-4 pb-1 text-micro text-zinc-500" data-testid="cout-du-run">
                {resumeDuCout(coutUsd, appels, outils)}
              </p>
            )}

            {/* Fil chronologique : agents, sécurité et validateur (ticket-257).
                Repli sur blocsDuPanneau si entries est vide — observateur arrivé
                après le début du run, sans historique (ticket-182). */}
            {entries.length > 0 ? (
              <FilDuRun entries={entries} />
            ) : (
              <>
                {coderStarted && (
                  <AgentBlock
                    agent="codeur"
                    tokens={currentTokens}
                    isActive={currentAgent === "codeur"}
                    isDone={coderDone}
                    doneContent={codeurDoneContent || undefined}
                  />
                )}
                {reviewerStarted && (
                  <AgentBlock
                    agent="reviewer"
                    tokens=""
                    isActive={currentAgent === "reviewer"}
                    isDone={status === "done"}
                    reviewContent={reviewerContent}
                  />
                )}
              </>
            )}

            {status === "done" && lastResult && (
              <PipelineSummary
                result={lastResult}
                durationMs={durationMs}
                runClosed={runClosed}
                livraisonData={livraisonData}
              />
            )}
          </>
        )}

        {status === "error" && (
          <div className="m-3 rounded-sm p-3 bg-red-900/30 border border-red-700/50 text-red-400 text-xs">
            <div className="font-semibold mb-1">Erreur</div>
            <div>{errorMessage ?? "Unknown error"}</div>
          </div>
        )}
      </div>

      {/* Footer actions */}
      {((status === "done" && runClosed) || status === "error") && (
        <div className="px-4 py-3 border-t border-zinc-700 shrink-0 flex gap-3">
          <button
            onClick={clear}
            className="inline-flex items-center gap-1 text-xs text-zinc-500 hover:text-zinc-200 transition-colors"
          >
            <IconCross size={12} /> Fermer
          </button>
        </div>
      )}

      {/* Parler à l'agent pendant qu'il travaille (ticket-066). */}
      <AgentDialogue
        pendingQuestion={pendingQuestion}
        questionExpireA={questionExpireA}
        enCours={status === "running" || status === "connecting"}
        onAnswer={answer}
        onInterject={interject}
        onStop={stop}
      />

      {/* Ce que le ticket a produit : runs, branche, PR (ticket-064). */}
      <TicketActivity
        projectId={project?.id ?? null}
        ticket={activeTicket}
        branch={lastResult?.branch ?? null}
      />
    </div>
  );
}
