import { useState } from "react";
import { BAND } from "../../design/layout";
import RegionTitle from "../../design/RegionTitle";
import RunCard from "./RunCard";
import ServicesLances from "./ServicesLances";
import AgentPanel from "../AgentPanel";
import RunHistorique from "../StatsView/RunHistorique";
import { INITIAL } from "../../hooks/streamState";
import type { UseRunActifResult } from "../../hooks/streamState";
import type { UseSupervisionResult } from "../../hooks/useSupervision";
import type { Project, ServiceActif } from "../../types/api";
import { projetDuRun } from "./projetDuRun";
import { useLimites } from "../../hooks/useLimites";

/**
 * Ce que l'IDE est en train de faire, sur tous les projets — ticket-129.
 *
 * `AgentPanel` ne montrait qu'un run, celui du projet actif, et seulement
 * depuis l'onglet qui l'avait lancé. Or le parallélisme réel de Tessera est
 * **entre projets** (ADR-038) : c'est exactement ce que rien n'affichait.
 *
 * Le détail réutilise `AgentPanel` tel quel plutôt qu'un second affichage :
 * deux vues d'un même run divergeraient, et c'est celle qu'on regarde le
 * moins qui dériverait (ADR-034).
 */
interface SupervisionViewProps {
  supervision: UseSupervisionResult;
  projects: Project[];
  /**
   * Les services lancés, listés à part des runs (ticket-138) : un service
   * n'a ni ticket, ni tours, ni verdict, et ne se termine pas tout seul.
   * Les mêler aux runs donnerait un chrono qui monte indéfiniment à côté de
   * pipelines qui finissent.
   */
  services?: ServiceActif[];
}

export default function SupervisionView({
  supervision,
  projects,
  services = [],
}: SupervisionViewProps) {
  const { runs, selection, selectionner, etatDe } = supervision;
  const limites = useLimites();

  // Run affiché en lecture seule — ticket-327.
  const [revisuRun, setRevisuRun] = useState<{ runId: string; ticketId: string } | null>(null);

  // Les runs qui attendent une réponse passent en tête (ticket-266).
  const runsTries = [...runs].sort((a, b) => {
    const aAttend = etatDe(a.run_id).pendingQuestion !== null;
    const bAttend = etatDe(b.run_id).pendingQuestion !== null;
    if (aAttend === bAttend) return 0;
    return aAttend ? -1 : 1;
  });

  // Sélection par défaut : un run en attente s'il y en a un, sinon le premier.
  // Un choix explicite de l'utilisateur (selection != null) garde la priorité.
  const runEnAttente = runs.find((r) => etatDe(r.run_id).pendingQuestion !== null);
  const selectionne =
    runs.find((r) => r.run_id === selection) ?? runEnAttente ?? runs[0];

  /** Sélectionne le run et donne le focus au champ de réponse (ticket-266). */
  function repondre(runId: string) {
    selectionner(runId);
    const input = document.getElementById("dialogue-reponse");
    if (input) {
      input.focus();
    } else {
      requestAnimationFrame(() => {
        document.getElementById("dialogue-reponse")?.focus();
      });
    }
  }

  return (
    <div className="flex h-full flex-col overflow-hidden bg-zinc-900">
      <div className={`${BAND} justify-between border-b border-zinc-800 px-3`}>
        <RegionTitle>Supervision</RegionTitle>
        <span className="text-micro text-zinc-500">
          {supervision.connecte ? etiquette(runs.length) : "hors ligne"}
        </span>
      </div>

      {services.length > 0 ? (
        <ServicesLances
          services={services}
          sortieDe={supervision.sortieDuService}
        />
      ) : null}

      {runs.length === 0 ? (
        <VueVide
          connecte={supervision.connecte}
          avecServices={services.length > 0}
        />
      ) : (
        <div className="grid min-h-0 flex-1 grid-cols-[minmax(240px,340px)_1fr] overflow-hidden">
          <div className="flex flex-col gap-2 overflow-y-auto border-r border-zinc-800 p-3">
            {runsTries.map((run) => {
              const etat = etatDe(run.run_id);
              return (
                <RunCard
                  key={run.run_id}
                  run={run}
                  etat={etat}
                  selectionne={run.run_id === selectionne?.run_id}
                  onSelect={() => {
                    setRevisuRun(null);
                    selectionner(run.run_id);
                  }}
                  plafondUsd={limites?.run_max_budget_usd ?? null}
                  onRepondre={
                    etat.pendingQuestion !== null
                      ? () => repondre(run.run_id)
                      : undefined
                  }
                  onRevoir={
                    etat.runClosed && run.db_run_id && run.ticket_id
                      ? () =>
                          setRevisuRun({
                            runId: run.db_run_id as string,
                            ticketId: run.ticket_id as string,
                          })
                      : undefined
                  }
                />
              );
            })}
          </div>

          <div className="min-h-0 overflow-hidden">
            {revisuRun ? (
              <RunHistorique
                runId={revisuRun.runId}
                ticketId={revisuRun.ticketId}
                onClose={() => setRevisuRun(null)}
              />
            ) : selectionne ? (
              <AgentPanel
                project={projetDuRun(projects, selectionne)}
                stream={projeter(supervision, selectionne.run_id)}
                onRevoirRun={(runId, ticketId) => setRevisuRun({ runId, ticketId })}
              />
            ) : null}
          </div>
        </div>
      )}
    </div>
  );
}

function etiquette(nombre: number): string {
  if (nombre === 0) return "rien en cours";
  return `${nombre} run${nombre > 1 ? "s" : ""}`;
}

function VueVide({
  connecte,
  avecServices,
}: {
  connecte: boolean;
  avecServices: boolean;
}) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-2 p-6 text-center">
      <p className="text-sm text-zinc-400">
        {!connecte
          ? "En attente du canal d'observation…"
          : avecServices
            ? "Aucun run en cours — mais des services tournent."
            : "Aucun run en cours."}
      </p>
      <p className="max-w-sm text-xs text-zinc-600">
        Lance un ticket depuis le tableau : il apparaîtra ici, quel que soit le
        projet, et restera visible même si tu changes de vue.
      </p>
    </div>
  );
}

/**
 * Donne à `AgentPanel` l'interface qu'il attend, pour un run quelconque.
 *
 * Les actions de lancement n'ont pas de sens ici — on observe un run qui
 * tourne déjà — mais le dialogue, lui, en a : depuis ticket-128 n'importe
 * quel client peut répondre à un agent, pas seulement celui qui a lancé.
 */
function projeter(
  supervision: UseSupervisionResult,
  runId: string,
): UseRunActifResult {
  const rien = () => undefined;
  return {
    ...(supervision.etatDe(runId) ?? INITIAL),
    connect: rien,
    connectQueue: rien,
    connectAutonome: rien,
    disconnect: rien,
    // « Fermer » retire la carte du run clos de la liste (ticket-267).
    clear: () => supervision.fermerRun(runId),
    answer: (text: string) =>
      supervision.envoyer(runId, { type: "answer", text }),
    interject: (text: string) =>
      supervision.envoyer(runId, { type: "interject", text }),
    stop: () => supervision.envoyer(runId, { type: "stop", text: "" }),
  };
}
