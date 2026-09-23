import { BAND } from "../../design/layout";
import RegionTitle from "../../design/RegionTitle";
import RunCard from "./RunCard";
import AgentPanel from "../AgentPanel";
import { INITIAL } from "../../hooks/streamState";
import type { UseRunActifResult } from "../../hooks/streamState";
import type { UseSupervisionResult } from "../../hooks/useSupervision";
import type { Project } from "../../types/api";

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
}

export default function SupervisionView({
  supervision,
  projects,
}: SupervisionViewProps) {
  const { runs, selection, selectionner, etatDe } = supervision;
  const selectionne = runs.find((r) => r.run_id === selection) ?? runs[0];

  return (
    <div className="flex h-full flex-col overflow-hidden bg-zinc-900">
      <div className={`${BAND} justify-between border-b border-zinc-800 px-3`}>
        <RegionTitle>Supervision</RegionTitle>
        <span className="text-micro text-zinc-500">
          {supervision.connecte ? etiquette(runs.length) : "hors ligne"}
        </span>
      </div>

      {runs.length === 0 ? (
        <VueVide connecte={supervision.connecte} />
      ) : (
        <div className="grid min-h-0 flex-1 grid-cols-[minmax(240px,340px)_1fr] overflow-hidden">
          <div className="flex flex-col gap-2 overflow-y-auto border-r border-zinc-800 p-3">
            {runs.map((run) => (
              <RunCard
                key={run.run_id}
                run={run}
                etat={etatDe(run.run_id)}
                selectionne={run.run_id === selectionne?.run_id}
                onSelect={() => selectionner(run.run_id)}
              />
            ))}
          </div>

          <div className="min-h-0 overflow-hidden">
            {selectionne ? (
              <AgentPanel
                project={
                  projects.find((p) => p.id === selectionne.project_id) ?? null
                }
                stream={projeter(supervision, selectionne.run_id)}
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

function VueVide({ connecte }: { connecte: boolean }) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-2 p-6 text-center">
      <p className="text-sm text-zinc-400">
        {connecte
          ? "Aucun run en cours."
          : "En attente du canal d'observation…"}
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
    clear: rien,
    answer: (text: string) => supervision.envoyer(runId, { type: "answer", text }),
    interject: (text: string) =>
      supervision.envoyer(runId, { type: "interject", text }),
    stop: () => supervision.envoyer(runId, { type: "stop", text: "" }),
  };
}
