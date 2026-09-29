import RegionTitle from "../../design/RegionTitle";
import { BAND } from "../../design/layout";
import AgentBlock from "../AgentPanel/AgentBlock";
import { resumeDuCout } from "../../lib/budget";
import PipelineSummary from "../AgentPanel/PipelineSummary";
import type { AgentRole, OrchestratorEvent } from "../../types/api";
import type { UseRunActifResult } from "../../hooks/streamState";

/**
 * Ce que le run est en train de faire, au centre de l'écran (ticket-075).
 *
 * Pendant un run, le centre affichait le tableau des tickets — ou, si on avait
 * demandé le diff, « ce ticket n'a jamais été lancé ». La seule fenêtre sur le
 * travail en cours était une colonne de 320 pixels à droite, où le flux d'un
 * agent défile dans un cadre de quelques lignes.
 *
 * Or c'est le moment où l'on a le plus besoin de place : ce que chaque agent
 * lit, écrit et conclut est ce qui permet de décider s'il faut intervenir ou
 * arrêter. Le centre le montre donc en grand, et la colonne de droite garde
 * ce qui sert à agir — répondre, infléchir, arrêter.
 */
interface RunViewProps {
  stream: UseRunActifResult;
}

function aFini(events: OrchestratorEvent[], agent: AgentRole): boolean {
  return events.some((e) => e.type === "agent_done" && e.agent === agent);
}

/** Le dernier contenu rendu par un agent, ou la chaîne vide. */
function dernierContenu(events: OrchestratorEvent[], agent: AgentRole): string {
  return (
    events
      .filter((e) => e.type === "agent_done" && e.agent === agent)
      .map((e) => (typeof e.data["content"] === "string" ? e.data["content"] : ""))
      .at(-1) ?? ""
  );
}

/**
 * Les agents qui ont parlé, dans leur ordre d'apparition.
 *
 * Dérivé des événements plutôt que d'une liste écrite à la main : `AgentRole`
 * ne couvre pas toutes les étapes du pipeline, et une liste figée afficherait
 * des blocs vides pour des agents qui n'ont pas tourné — ce qui donnerait
 * l'impression qu'il ne se passe rien.
 */
function agentsQuiOntParle(events: OrchestratorEvent[]): AgentRole[] {
  const vus: AgentRole[] = [];
  for (const e of events) {
    if (e.type === "agent_started" && e.agent && !vus.includes(e.agent)) {
      vus.push(e.agent);
    }
  }
  return vus;
}

export default function RunView({ stream }: RunViewProps) {
  const { events, currentAgent, currentRound, currentTokens, lastResult, queue } =
    stream;

  const demarres = agentsQuiOntParle(events);

  return (
    <div className="flex h-full flex-col bg-zinc-900">
      <div className={`${BAND} justify-between gap-3 border-b border-zinc-700 px-4`}>
        <RegionTitle>Run en cours</RegionTitle>
        <div className="flex items-center gap-3 text-mini text-zinc-400">
          {queue && (
            <span className="text-violet-300">
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
          {currentAgent && (
            <span className="text-blue-300">{currentAgent.toUpperCase()}</span>
          )}
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto py-3">
        {demarres.length === 0 && (
          <p className="px-4 text-xs text-zinc-500">
            Le run démarre : la branche se crée et le premier agent se prépare.
          </p>
        )}

        {demarres.map((agent) => (
          <AgentBlock
            key={agent}
            agent={agent}
            tokens={agent === "codeur" ? currentTokens : ""}
            isActive={currentAgent === agent}
            isDone={aFini(events, agent)}
            reviewContent={
              agent === "reviewer" ? dernierContenu(events, agent) : undefined
            }
            doneContent={
              agent === "codeur" ? dernierContenu(events, agent) : undefined
            }
          />
        ))}

        {lastResult && <PipelineSummary result={lastResult} />}
      </div>
    </div>
  );
}
