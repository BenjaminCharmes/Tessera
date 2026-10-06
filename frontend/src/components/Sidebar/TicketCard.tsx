import {
  IconDiff,
  IconDot,
  IconPlay,
  IconQueue,
} from "../../design/icons";
import { memo, useEffect, useRef, useState } from "react";
import { api } from "../../lib/api";
import { MIME_TICKET, transitionsManuelles } from "../../lib/transitionsManuelles";
import { useFenetreVisible } from "../../hooks/useFenetreVisible";
import type {
  PRStatus,
  Ticket,
  TicketPriority,
  TicketStatus,
} from "../../types/api";

const STATUS_STYLE: Record<TicketStatus, string> = {
  todo: "bg-zinc-700 text-zinc-300",
  "in-progress": "bg-blue-900 text-blue-300",
  "in-review": "bg-amber-900 text-amber-300",
  done: "bg-green-900 text-green-300",
  blocked: "bg-red-900 text-red-300",
  cancelled: "bg-zinc-800 text-zinc-400",
};

const PRIORITY_STYLE: Record<TicketPriority, string> = {
  critical: "bg-red-900 text-red-300",
  high: "bg-amber-900 text-amber-300",
  medium: "bg-zinc-700 text-zinc-400",
  low: "bg-zinc-800 text-zinc-500",
};

// Pas d'icône ici : `CI_STYLE` porte déjà la couleur du rôle — ambre en
// attente, vert au succès, rouge à l'échec. Une émoji par-dessus répétait
// l'information et changeait de dessin selon la machine (ticket-067).
const CI_LABEL: Record<string, string> = {
  pending: "CI en cours",
  passing: "CI verte",
  failing: "CI en échec",
  none: "CI N/A",
};

const CI_STYLE: Record<string, string> = {
  pending: "bg-amber-900 text-amber-300 animate-pulse",
  passing: "bg-green-900 text-green-300",
  failing: "bg-red-900 text-red-300",
  none: "bg-zinc-700 text-zinc-400",
};

const PR_STATE_LABEL: Record<string, string> = {
  open: "PR ouverte",
  closed: "PR fermée",
  merged: "PR mergée",
};

const POLL_INTERVAL_MS = 30_000;

interface TicketCardProps {
  ticket: Ticket;
  isActive: boolean;
  isRunning: boolean;
  runningRound?: number;
  /** Nombre de tours du run quand le backend le dit ; sinon le badge ne compte pas (ticket-123). */
  maxRounds?: number | null;
  githubRemote?: string | null;
  onSelect: (ticket: Ticket) => void;
  onRun: (ticketId: string) => void;
  onShowDiff?: (ticketId: string) => void;
  onToggleQueue?: (ticketId: string) => void;
  dansLaFile?: boolean;
  /**
   * Changer le statut à la main (ticket-194). Absent : ni menu ni
   * glisser-déposer. Un ticket en cours de run n'en a jamais — le verrou
   * d'ADR-038 le tient.
   */
  onChangeStatus?: (ticketId: string, status: TicketStatus) => void;
  /**
   * La cause d'un blocage, portée en infobulle sur le badge de statut
   * (ticket-218). Optionnel : seul le contexte qui connaît l'activité du
   * ticket peut le fournir.
   */
  arret?: string | null;
  /**
   * Amène le run de ce ticket au centre (ticket-283). Quand fourni et que le
   * ticket est en cours, le rond bleu devient un bouton « Voir le run » actif
   * au lieu d'un indicateur désactivé.
   */
  onVoirLeRun?: () => void;
}

/**
 * Carte d'un ticket dans la colonne latérale.
 *
 * Enveloppée dans `React.memo` : avec des callbacks stables en amont, elle ne
 * se redessine pas quand un événement de run arrive pour un autre composant
 * (ticket-354).
 */
const TicketCard = memo(function TicketCard({
  ticket,
  isActive,
  isRunning,
  runningRound,
  maxRounds,
  githubRemote,
  onSelect,
  onRun,
  onShowDiff,
  onToggleQueue,
  dansLaFile = false,
  onChangeStatus,
  arret,
  onVoirLeRun,
}: TicketCardProps) {
  const canRun = ticket.status !== "done" && ticket.status !== "cancelled";
  const transitions = transitionsManuelles(ticket.status);
  const peutChangerDeStatut =
    !!onChangeStatus && !isRunning && transitions.length > 0;
  const [prStatus, setPrStatus] = useState<PRStatus | null>(null);
  const fenetreVisible = useFenetreVisible();

  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    // Pas de polling sans PR, ni quand la fenêtre est cachée (ticket-356).
    if (!ticket.pr_number || !githubRemote || !fenetreVisible) return;

    const fetchStatus = async () => {
      try {
        const s = await api.github.getPrStatus(ticket.project_id, ticket.id);
        setPrStatus(s);
        if (s.state === "merged" || s.state === "closed") {
          if (intervalRef.current) clearInterval(intervalRef.current);
        }
      } catch (err) {
        // Une erreur 4xx ne changera pas au prochain essai : un pr_number
        // hérité d'un autre dépôt renvoie 404 pour toujours. Réessayer toutes
        // les 30 s, sur chaque carte, épuisait le quota GitHub (ticket-217).
        // Une 5xx peut être passagère, on continue.
        if (err instanceof Error && /^API 4\d\d\b/.test(err.message)) {
          if (intervalRef.current) clearInterval(intervalRef.current);
        }
      }
    };

    fetchStatus();
    intervalRef.current = setInterval(fetchStatus, POLL_INTERVAL_MS);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [ticket.pr_number, ticket.project_id, ticket.id, githubRemote, fenetreVisible]);

  // La carte est un `div` cliquable : sans rôle ni focus, elle n'existait pas
  // au clavier. Seule la carte elle-même réagit à Entrée et Espace — la
  // les boutons internes ont leurs propres touches
  // (ticket-123).
  function handleKeyDown(e: React.KeyboardEvent<HTMLDivElement>) {
    if (e.target !== e.currentTarget) return;
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      onSelect(ticket);
    }
  }

  return (
    <div
      role="button"
      tabIndex={0}
      aria-pressed={isActive}
      onClick={() => onSelect(ticket)}
      onKeyDown={handleKeyDown}
      draggable={peutChangerDeStatut}
      onDragStart={(e) => {
        if (!peutChangerDeStatut) return;
        e.dataTransfer.setData(
          MIME_TICKET,
          JSON.stringify({ id: ticket.id, status: ticket.status }),
        );
        e.dataTransfer.effectAllowed = "move";
      }}
      className={`relative mx-2 mb-1 p-2 rounded cursor-pointer transition-colors focus-visible:outline-hidden focus-visible:ring-1 focus-visible:ring-zinc-400 ${
        isActive ? "bg-zinc-700" : "hover:bg-zinc-800"
      }`}
    >
      <div className="flex items-start gap-1">
        <div className="flex-1 min-w-0">
          <div className="text-micro text-zinc-600 font-mono">{ticket.id}</div>
          <div className="text-xs text-zinc-200 leading-tight mt-0.5 line-clamp-2">
            {ticket.title}
          </div>
          <div className="flex items-center gap-1 mt-1 flex-wrap">
            {peutChangerDeStatut ? (
              <select
                aria-label={`Statut de ${ticket.id}`}
                value={ticket.status}
                onClick={(e) => e.stopPropagation()}
                onKeyDown={(e) => e.stopPropagation()}
                onChange={(e) => {
                  e.stopPropagation();
                  onChangeStatus?.(ticket.id, e.target.value as TicketStatus);
                }}
                className={`text-micro px-1 py-0.5 rounded-sm font-medium border-0 outline-hidden cursor-pointer ${STATUS_STYLE[ticket.status]}`}
              >
                <option value={ticket.status}>{ticket.status}</option>
                {transitions.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            ) : (
              <span
                className={`text-micro px-1.5 py-0.5 rounded-sm font-medium ${STATUS_STYLE[ticket.status]}`}
                title={
                  ticket.status === "blocked" && arret ? arret : undefined
                }
              >
                {ticket.status}
              </span>
            )}
            <span
              className={`text-micro px-1.5 py-0.5 rounded-sm font-medium ${PRIORITY_STYLE[ticket.priority]}`}
            >
              {ticket.priority}
            </span>
            {isRunning && runningRound != null && runningRound > 0 && (
              <span className="text-micro px-1.5 py-0.5 rounded-sm font-medium bg-blue-900 text-blue-300 animate-pulse">
                tour {runningRound}
                {maxRounds != null && maxRounds > 0 ? `/${maxRounds}` : ""}
              </span>
            )}
            {ticket.pr_number !== null && (
              <a
                href={prStatus?.pr_url ?? "#"}
                target="_blank"
                rel="noopener noreferrer"
                onClick={(e) => e.stopPropagation()}
                title={
                  prStatus
                    ? PR_STATE_LABEL[prStatus.state]
                    : `PR #${ticket.pr_number}`
                }
                className="text-micro px-1.5 py-0.5 rounded-sm font-medium bg-zinc-800 text-zinc-300 hover:bg-zinc-700 transition-colors"
              >
                PR #{ticket.pr_number}
              </a>
            )}
            {prStatus && (
              <span
                className={`text-micro px-1.5 py-0.5 rounded-sm font-medium ${CI_STYLE[prStatus.ci_status]}`}
              >
                {CI_LABEL[prStatus.ci_status]}
              </span>
            )}
          </div>
        </div>

        <div className="flex flex-col gap-0.5 shrink-0">
          {canRun && (
            isRunning && onVoirLeRun ? (
              /* Ticket en cours : le rond devient un raccourci « Voir le run »
                 actif (ticket-283) — au lieu d'un indicateur désactivé. */
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onVoirLeRun();
                }}
                title="Voir le run"
                aria-label="Voir le run"
                className="w-6 h-6 flex items-center justify-center rounded-sm transition-colors text-blue-300 hover:bg-zinc-600"
              >
                <IconDot size={8} className="animate-pulse text-blue-400" />
              </button>
            ) : (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onRun(ticket.id);
                }}
                disabled={isRunning}
                title="Lancer le pipeline"
                aria-label="Lancer le pipeline"
                className="w-6 h-6 flex items-center justify-center rounded-sm transition-colors text-zinc-500 hover:text-zinc-200 hover:bg-zinc-600 disabled:cursor-not-allowed"
              >
                {isRunning ? (
                  <IconDot size={8} className="animate-pulse text-blue-400" />
                ) : (
                  <IconPlay size={12} />
                )}
              </button>
            )
          )}
          {/* Même condition que le bouton « Lancer » : les deux mènent au
              même endroit, ils obéissent à la même règle. La file acceptait
              un ticket terminé et le relançait pour de bon (ticket-115). */}
          {onToggleQueue && canRun && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onToggleQueue(ticket.id);
              }}
              title={dansLaFile ? "Retirer de la file" : "Ajouter à la file"}
              aria-label={dansLaFile ? "Retirer de la file" : "Ajouter à la file"}
              className={`flex h-6 w-6 items-center justify-center rounded transition-colors ${
                dansLaFile
                  ? "bg-violet-500/20 text-zinc-100"
                  : "text-zinc-500 hover:bg-zinc-600 hover:text-zinc-300"
              }`}
            >
              <IconQueue size={12} />
            </button>
          )}
          {/* Relire ce que le run a produit : c'est ce qui manquait pour
              juger un ticket sans ouvrir VSCode (ticket-069). */}
          {onShowDiff && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onShowDiff(ticket.id);
              }}
              title="Voir le diff"
              aria-label="Voir le diff"
              className="w-6 h-6 flex items-center justify-center rounded-sm transition-colors text-zinc-500 hover:text-zinc-300 hover:bg-zinc-600"
            >
              <IconDiff size={12} />
            </button>
          )}
          {/* Plus de bouton « Ouvrir une PR » : il ne poussait rien, visait une
              branche `ticket-XXX` que les runs ne créent pas, et s'affichait
              sur des tickets déjà mergés faute de `pr_number`. Le panneau
              d'activité pousse puis ouvre la PR (ticket-205). */}
        </div>
      </div>
    </div>
  );
});

export default TicketCard;
