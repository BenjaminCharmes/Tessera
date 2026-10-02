import { BAND } from "../../design/layout";
import RegionTitle from "../../design/RegionTitle";
import { useEffect, useRef } from "react";
import type { OrchestratorEvent } from "../../types/api";

interface BottomPanelProps {
  events: OrchestratorEvent[];
  /** Nom du projet dont on affiche le run — quand la sélection de Supervision
   *  diffère du projet actif (ticket-283). Absent : le projet actif. */
  projetLabel?: string | null;
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
    "l'arbre de travail contient des modifications hors pipeline",
  commit_failed:
    "le commit de fin de run a échoué : le travail est resté dans l'arbre et le ticket n'est pas passé done.",
};

function raisonLisible(ev: OrchestratorEvent): string {
  const reason = ev.data["reason"];
  const message = ev.data["message"];
  const fichiers = ev.data["fichiers"];
  const fichiersSuffix =
    Array.isArray(fichiers) && fichiers.length > 0
      ? ` : ${fichiers.join(", ")}`
      : "";
  if (typeof reason === "string") {
    const lisible = RAISONS[reason] ?? reason;
    const withFiles = `${lisible}${fichiersSuffix}`;
    return typeof message === "string" ? `${withFiles} (${message})` : withFiles;
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

/**
 * Ce que la livraison a fait du commit, en une ligne (ticket-083).
 *
 * L'arrêt compte autant que la réussite : un run qui s'arrête sans le dire se
 * lit comme une panne, alors que la plupart des arrêts sont le comportement
 * voulu — le projet n'a simplement pas déclaré d'aller plus loin.
 */
function livraisonLisible(ev: OrchestratorEvent): string {
  const pr = ev.data["pr_number"];
  const arret = ev.data["arret"];
  if (ev.data["merged"]) return `PR #${String(pr)} mergée`;
  if (arret) return String(arret);
  if (pr) return `PR #${String(pr)} ouverte`;
  return "Livraison terminée";
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
    case "livraison_done":
      return `[${t}] ${livraisonLisible(ev)}`;
    case "documentation_failed":
      return `[${t}] Documentation : échec — ${String(ev.data["error"] ?? "raison inconnue")}`;
    case "security_audit_started":
      return `[${t}] Audit sécurité : démarré`;
    case "security_audit_done": {
      const verdict = typeof ev.data["verdict"] === "string" ? ev.data["verdict"] : "inconnu";
      return `[${t}] Audit sécurité : ${verdict}`;
    }
    case "validation_started":
      return `[${t}] Validation : démarrée`;
    case "validation_done": {
      // Le champ `approved` est ajouté depuis ticket-279 ; les backends plus
      // anciens n'émettent que `verdict` — on retombe sur lui en dernier recours.
      const hasApproved = "approved" in ev.data;
      const approved = hasApproved
        ? ev.data["approved"] === true
        : typeof ev.data["verdict"] === "string"
          ? ev.data["verdict"] === "APPROVED"
          : false;
      return `[${t}] Validation : ${approved ? "approuvée" : "refusée"}`;
    }
    case "documentation_started":
      return `[${t}] Documentation : démarrée`;
    case "doc_updated":
      return `[${t}] Documentation mise à jour`;
    case "livraison_started":
      return `[${t}] Livraison : démarrée`;
    case "test_result": {
      // Une suite rouge renvoie le travail au codeur sans passer par la revue
      // (ticket-098) ; sans ligne dans le log, trois tours de codeur s'affichaient
      // d'affilée sans raison apparente (ticket-279).
      const passed = ev.data["passed"] === true;
      return `[${t}] Tests : ${passed ? "verts" : "rouges — retour au codeur"}`;
    }
    case "error":
      return `[${t}] Erreur : ${raisonLisible(ev)}`;
    default:
      return null;
  }
}

export default function BottomPanel({ events, projetLabel }: BottomPanelProps) {
  const bottomRef = useRef<HTMLDivElement>(null);
  const lines = events.map(eventToLine).filter((l): l is string => l !== null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [lines.length]);

  return (
    <div className="h-full flex flex-col bg-zinc-950 border-t border-zinc-700">
      <div className={`${BAND} gap-4 border-b border-zinc-700 px-4`}>
        <RegionTitle>Pipeline log{projetLabel ? ` — ${projetLabel}` : ""}</RegionTitle>
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
