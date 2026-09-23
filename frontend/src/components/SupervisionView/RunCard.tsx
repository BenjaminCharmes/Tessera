import Chrono from "./Chrono";
import type { StreamState } from "../../hooks/streamState";
import type { RunActif } from "../../types/api";

/**
 * Un run, tel qu'on le lit d'un coup d'œil — ticket-129.
 *
 * ADR-026 : les états n'empruntent qu'aux cinq familles, et l'accent
 * d'identité est une **barre**, jamais la couleur d'un mot. Le nom du projet
 * se rend donc en neutre, et c'est la barre de gauche qui dit « c'est celui-ci
 * que tu regardes ».
 */
interface RunCardProps {
  run: RunActif;
  etat: StreamState;
  selectionne: boolean;
  onSelect: () => void;
}

const LIBELLE_DU_MODE: Record<string, string> = {
  single: "ticket",
  queue: "file",
  autonomous: "autonome",
};

export default function RunCard({
  run,
  etat,
  selectionne,
  onSelect,
}: RunCardProps) {
  const attend = etat.pendingQuestion !== null;
  const echoue = etat.status === "error";

  return (
    <button
      type="button"
      onClick={onSelect}
      aria-pressed={selectionne}
      aria-label={`Run ${run.ticket_id ?? run.mode} sur ${run.project_id}`}
      className={`flex w-full gap-3 rounded-md border p-3 text-left transition-colors ${
        selectionne
          ? "border-zinc-700 bg-zinc-800/60"
          : "border-zinc-800 bg-zinc-900 hover:bg-zinc-800/40"
      }`}
    >
      {/* La barre d'identité : violette quand c'est le run regardé. */}
      <span
        aria-hidden
        className={`w-0.5 shrink-0 rounded-full ${
          selectionne ? "bg-violet-400" : "bg-transparent"
        }`}
      />
      <span className="min-w-0 flex-1">
        <span className="flex items-baseline justify-between gap-2">
          <span className="truncate text-sm text-zinc-200">
            {run.project_id}
          </span>
          <span className="shrink-0 text-micro text-zinc-500">
            {LIBELLE_DU_MODE[run.mode] ?? run.mode}
          </span>
        </span>

        <span className="mt-1 flex items-baseline justify-between gap-2">
          <span className="truncate text-xs text-zinc-400">
            {run.ticket_id ?? "—"}
          </span>
          <span className="shrink-0 text-micro tabular-nums text-zinc-500">
            <Chrono depuis={run.demarre_a} />
          </span>
        </span>

        <span className="mt-2 flex flex-wrap items-center gap-1.5">
          {echoue ? (
            <Etiquette classe="bg-red-500/20 text-red-200">bloqué</Etiquette>
          ) : attend ? (
            <Etiquette classe="bg-amber-500/20 text-amber-200">
              attend une réponse
            </Etiquette>
          ) : (
            <Etiquette classe="bg-blue-500/20 text-blue-200">
              {etat.currentAgent ?? "en cours"}
            </Etiquette>
          )}
          {etat.currentRound > 0 ? (
            <Etiquette classe="bg-zinc-800 text-zinc-400">
              tour {etat.currentRound}
            </Etiquette>
          ) : null}
          {run.cout_usd > 0 ? (
            <Etiquette classe="bg-zinc-800 text-zinc-400">
              ${run.cout_usd.toFixed(2)}
            </Etiquette>
          ) : null}
        </span>
      </span>
    </button>
  );
}

function Etiquette({
  children,
  classe,
}: {
  children: React.ReactNode;
  classe: string;
}) {
  return (
    <span className={`rounded-sm px-1.5 py-0.5 text-micro ${classe}`}>
      {children}
    </span>
  );
}
