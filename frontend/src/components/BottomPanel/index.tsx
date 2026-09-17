import { BAND } from "../../design/layout";
import RegionTitle from "../../design/RegionTitle";
import { useEffect, useRef } from "react";
import type { OrchestratorEvent } from "../../types/api";

interface BottomPanelProps {
  events: OrchestratorEvent[];
}

/**
 * Ce qu'une erreur de pipeline dit à l'utilisateur.
 *
 * Le formateur ne lisait que `message`, alors que les refus du pipeline
 * portent `reason`. Un arbre de travail sale s'affichait donc « Erreur:
 * unknown » — la raison exacte était dans l'événement, jetée à l'affichage
 * (ticket-068).
 *
 * Une raison inconnue est montrée telle quelle : mieux vaut un identifiant
 * technique qu'un mot qui n'apprend rien.
 */
const RAISONS: Record<string, string> = {
  dirty_working_tree:
    "l'arbre de travail contient des modifications que le pipeline n'a pas faites. Commite-les ou remise-les avant de relancer.",
  commit_failed:
    "le commit de fin de run a échoué : le travail est resté dans l'arbre et le ticket n'est pas passé done.",
};

function raisonLisible(ev: OrchestratorEvent): string {
  const reason = ev.data["reason"];
  const message = ev.data["message"];
  if (typeof reason === "string") {
    const lisible = RAISONS[reason] ?? reason;
    return typeof message === "string" ? `${lisible} (${message})` : lisible;
  }
  return typeof message === "string" ? message : "raison non précisée";
}

function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString("fr-FR", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function eventToLine(ev: OrchestratorEvent): string | null {
  const t = formatTime(ev.timestamp);
  switch (ev.type) {
    case "ticket_status_changed":
      return `[${t}] ${ev.ticket_id} : ${String(ev.data["status"] ?? "")}`;
    case "agent_started":
      return `[${t}] ${ev.agent ?? "?"} démarré (tour ${String(ev.data["round"] ?? "?")})`;
    case "agent_done":
      return `[${t}] ${ev.agent ?? "?"} terminé`;
    case "pipeline_done":
      return `[${t}] Pipeline terminé — ${ev.data["approved"] ? "APPROVED" : "CHANGES_REQUESTED"} : ${String(ev.data["final_status"] ?? "")}`;
    case "error":
      return `[${t}] Erreur : ${raisonLisible(ev)}`;
    default:
      return null;
  }
}

export default function BottomPanel({ events }: BottomPanelProps) {
  const bottomRef = useRef<HTMLDivElement>(null);
  const lines = events.map(eventToLine).filter((l): l is string => l !== null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [lines.length]);

  return (
    <div className="h-full flex flex-col bg-zinc-950 border-t border-zinc-700">
      <div className={`${BAND} gap-4 border-b border-zinc-700 px-4`}>
        <RegionTitle>Pipeline log</RegionTitle>
      </div>
      <div className="flex-1 overflow-y-auto px-4 py-2 text-xs font-mono">
        {lines.length === 0 ? (
          <span className="text-zinc-700">— en attente d'un pipeline —</span>
        ) : (
          lines.map((line, i) => (
            <div key={i} className="text-zinc-400 leading-5">
              {line}
            </div>
          ))
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
