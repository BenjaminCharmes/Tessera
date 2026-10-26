import Chrono from "./Chrono";
import { clotureDuRun, etatAffiche } from "./etatDuRun";
import Button from "../../design/ui/Button";
import StatusPill from "../../design/ui/StatusPill";
import LienTicket from "../../design/ui/LienTicket";
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
  /**
   * Quand le run attend une réponse, sélectionne ce run et donne le focus
   * au champ de réponse dans AgentDialogue (ticket-266).
   */
  onRepondre?: () => void;
  /**
   * « Répondre » est l'action principale de la vue (bouton plein) : une seule
   * carte à la fois, sinon la vue aurait plusieurs boutons pleins (ticket-442).
   */
  reponsePrincipale?: boolean;
  /**
   * Ouvre la vue en lecture seule du run terminé (ticket-327).
   * Présent uniquement si le run est clos et que `run.db_run_id` est renseigné.
   */
  onRevoir?: () => void;
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
  onRepondre,
  reponsePrincipale = false,
  onRevoir,
}: RunCardProps) {
  const attend = etat.pendingQuestion !== null;
  // Un tour de chat écrit et commite comme un run (ADR-019), mais il n'a ni
  // ticket, ni tours de revue, ni verdict. Lui afficher les étiquettes d'un
  // pipeline donnerait à lire des cases vides comme une information.
  const estUnChat = run.mode === "chat";

  return (
    <div
      onClick={onSelect}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onSelect();
        }
      }}
      role="button"
      tabIndex={0}
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
            {estUnChat || !run.ticket_id ? (
              estUnChat ? "conversation" : "—"
            ) : (
              <LienTicket projectId={run.project_id} ticketId={run.ticket_id} />
            )}
          </span>
          <span className="shrink-0 text-micro tabular-nums text-zinc-500">
            <Chrono
              depuis={run.demarre_a}
              termineA={clotureDuRun(etat)}
            />
          </span>
        </span>

        {/* Titre du ticket sous le numéro (ticket-286). */}
        {!estUnChat && run.ticket_titre ? (
          <span
            className="mt-0.5 block truncate text-micro text-zinc-500"
            title={run.ticket_titre}
          >
            {run.ticket_titre}
          </span>
        ) : null}

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
                    fait · <LienTicket projectId={run.project_id} ticketId={t} />
                  </span>
                ))}
                <span className="block truncate text-zinc-300">
                  en cours ·{" "}
                  {run.ticket_id ? (
                    <LienTicket projectId={run.project_id} ticketId={run.ticket_id} />
                  ) : (
                    "—"
                  )}
                </span>
                {(run.file_restants ?? []).map((t) => (
                  <span key={t} className="block truncate text-zinc-500">
                    ensuite · <LienTicket projectId={run.project_id} ticketId={t} />
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

        {/* Répondre directement depuis la carte (ticket-266). Plein quand c'est
            l'action principale de la vue, bordé pour les autres cartes. */}
        {attend && onRepondre ? (
          <span className="mt-2 flex">
            <Button
              variante={reponsePrincipale ? "plein" : "borde"}
              taille="compact"
              onClick={(e) => {
                e.stopPropagation();
                onRepondre();
              }}
            >
              Répondre
            </Button>
          </span>
        ) : null}

        <span className="mt-2 flex flex-wrap items-center gap-1.5">
          <StatusPill {...etatAffiche(etat)} />
          {etat.currentRound > 0 && !estUnChat ? (
            <StatusPill etat="neutre" libelle={`tour ${etat.currentRound}`} />
          ) : null}
          {run.cout_usd > 0 || (run.outils ?? 0) > 0 ? (
            <Etiquette classe={CLASSES_DE_BUDGET[couleurDuBudget(run.cout_usd, plafondUsd)]}>
              {resumeDuCout(run.cout_usd, run.appels ?? 0, run.outils ?? 0, plafondUsd)}
            </Etiquette>
          ) : null}
        </span>

        {/* État CI/merge de la PR livrée — ticket-308.
            Visible seulement si une PR a été ouverte. Couleurs ADR-026 :
            amber = attente, green = succès, red = échec. */}
        {etat.livraisonPrNumber !== null ? (
          <span className="mt-1.5 block">
            {etat.ciMerge === null ? (
              <StatusPill
                etat="attention"
                libelle={`PR #${etat.livraisonPrNumber} — en attente de CI`}
              />
            ) : etat.ciMerge.merged ? (
              <StatusPill etat="reussi" libelle={`PR #${etat.livraisonPrNumber} mergée`} />
            ) : (
              <StatusPill
                etat="echec"
                libelle={etat.ciMerge.arret ?? `PR #${etat.livraisonPrNumber} bloquée`}
              />
            )}
          </span>
        ) : null}

        {/* Bouton d'accès à la vue en lecture seule — ticket-327.
            Visible uniquement quand le run est clos et que son id en base est connu. */}
        {etat.runClosed && run.db_run_id && onRevoir ? (
          <span className="mt-2 flex">
            <Button
              taille="compact"
              onClick={(e) => {
                e.stopPropagation();
                onRevoir();
              }}
            >
              Revoir le run
            </Button>
          </span>
        ) : null}
      </span>
    </div>
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
