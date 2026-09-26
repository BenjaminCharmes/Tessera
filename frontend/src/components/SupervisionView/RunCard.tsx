import Chrono from "./Chrono";
import CompteARebours from "../AgentPanel/CompteARebours";
import { CLASSES_DE_BUDGET, couleurDuBudget, resumeDuCout } from "../../lib/budget";
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
  /** Le plafond du run, pour situer son coût (ticket-197). */
  plafondUsd?: number | null;
}

const LIBELLE_DU_MODE: Record<string, string> = {
  single: "ticket",
  queue: "file",
  autonomous: "autonome",
  chat: "chat",
};

export default function RunCard({
  run,
  etat,
  selectionne,
  onSelect,
  plafondUsd = null,
}: RunCardProps) {
  const attend = etat.pendingQuestion !== null;
  const echoue = etat.status === "error";
  // Un tour de chat écrit et commite comme un run (ADR-019), mais il n'a ni
  // ticket, ni tours de revue, ni verdict. Lui afficher les étiquettes d'un
  // pipeline donnerait à lire des cases vides comme une information.
  const estUnChat = run.mode === "chat";

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
          <span className="shrink-0 text-micro tabular-nums text-zinc-500">
            {LIBELLE_DU_MODE[run.mode] ?? run.mode}
            {/* Une file est *un* run, donc une carte : sans l'avancement, rien
                ne disait qu'il en restait deux derrière (ticket-172). */}
            {(run.file_total ?? 0) > 0
              ? ` ${run.file_index}/${run.file_total}`
              : ""}
          </span>
        </span>

        <span className="mt-1 flex items-baseline justify-between gap-2">
          <span className="truncate text-xs text-zinc-400">
            {estUnChat ? "conversation" : (run.ticket_id ?? "—")}
          </span>
          <span className="shrink-0 text-micro tabular-nums text-zinc-500">
            <Chrono depuis={run.demarre_a} />
          </span>
        </span>

        {/* Lu depuis le réseau : un backend plus ancien n'envoie pas encore
            ces champs, et une carte ne doit pas disparaître pour ça.
            Replié par défaut : ce qu'une carte montre sans qu'on l'ouvre se
            paie sur chacune d'elles (ticket-179). */}
        {(run.file_faits ?? []).length > 0 ||
        (run.file_restants ?? []).length > 0 ? (
          <span
            className="mt-1 block"
            onClick={(e) => e.stopPropagation()}
            role="presentation"
          >
            <details className="text-micro">
              <summary className="cursor-pointer text-zinc-600 hover:text-zinc-400">
                la file
              </summary>
              <span className="mt-1 block space-y-0.5">
                {(run.file_faits ?? []).map((t) => (
                  <span key={t} className="block truncate text-zinc-600">
                    fait · {t}
                  </span>
                ))}
                <span className="block truncate text-zinc-300">
                  en cours · {run.ticket_id ?? "—"}
                </span>
                {(run.file_restants ?? []).map((t) => (
                  <span key={t} className="block truncate text-zinc-500">
                    ensuite · {t}
                  </span>
                ))}
              </span>
            </details>
          </span>
        ) : null}

        {/* La question elle-même, et jusqu'à quand elle vaut : l'étiquette
            seule disait qu'on attendait, sans dire quoi ni combien de temps
            (ticket-186). */}
        {attend ? (
          <span className="mt-2 block">
            <span className="block rounded-sm border border-amber-900/60 bg-amber-950/30 px-2 py-1.5 text-mini text-amber-100">
              {etat.pendingQuestion}
            </span>
            <CompteARebours expireA={etat.questionExpireA} />
          </span>
        ) : null}

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
          {etat.currentRound > 0 && !estUnChat ? (
            <Etiquette classe="bg-zinc-800 text-zinc-400">
              tour {etat.currentRound}
            </Etiquette>
          ) : null}
          {run.cout_usd > 0 || (run.outils ?? 0) > 0 ? (
            <Etiquette classe={CLASSES_DE_BUDGET[couleurDuBudget(run.cout_usd, plafondUsd)]}>
              {resumeDuCout(run.cout_usd, run.appels ?? 0, run.outils ?? 0, plafondUsd)}
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
