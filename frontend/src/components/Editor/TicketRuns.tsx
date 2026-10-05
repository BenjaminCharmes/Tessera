import { useMemo, useState } from "react";
import { api } from "../../lib/api";
import { useResource } from "../../hooks/useResource";
import type { TicketRunSummary } from "../../types/api";

interface TicketRunsProps {
  projectId: string;
  ticketId: string;
  /** Ouvre la vue en lecture seule du run (ticket-281). */
  onRevoir: (runId: string) => void;
}

/** Au-delà, les runs plus anciens se replient derrière un bouton (ticket-333). */
const VISIBLES = 3;

function dateCourte(iso: string): string {
  return new Date(iso).toLocaleString("fr-FR", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/**
 * Les runs terminés d'un ticket, sous l'en-tête de son fichier — ticket-332.
 *
 * Le ticket-327 avait posé « Revoir le run » dans `TicketActivity`, que seule
 * la Supervision affiche encore : on ne le trouvait pas. Un run non terminé
 * (enveloppe de file, run en cours) n'a rien à relire et n'est pas proposé.
 * Une lecture qui échoue, ou aucun run terminé : la bande ne s'affiche pas.
 *
 * Seuls les trois derniers sont visibles d'emblée ; dépliée, la bande garde
 * une hauteur bornée et défile, pour ne jamais pousser le ticket hors de
 * l'écran (ticket-333).
 */
export default function TicketRuns({ projectId, ticketId, onRevoir }: TicketRunsProps) {
  const fetcher = useMemo(
    () => () => api.tickets.runs(projectId, ticketId),
    [projectId, ticketId],
  );
  const { data } = useResource<TicketRunSummary[] | null>(fetcher, null);
  const termines = (data ?? []).filter((r) => r.finished_at);
  const [deplie, setDeplie] = useState(false);

  if (termines.length === 0) return null;

  const caches = termines.length - VISIBLES;
  const affiches = deplie ? termines : termines.slice(0, VISIBLES);

  return (
    <div className="border-b border-zinc-800 bg-zinc-900 px-3 py-1.5 text-xs">
      <ul aria-label="Runs de ce ticket" className="max-h-40 space-y-0.5 overflow-y-auto">
        {affiches.map((r) => (
          <li key={r.id} className="flex items-baseline gap-3">
            <span className={r.approved ? "text-green-400" : "text-amber-400"}>
              {r.approved ? "approuvé" : (r.final_status ?? "terminé")}
            </span>
            <span className="tabular-nums text-zinc-500">
              {dateCourte(r.started_at)} · {r.rounds ?? 0} tour(s) · {r.total_cost_usd.toFixed(2)} $
            </span>
            <button
              type="button"
              onClick={() => onRevoir(r.id)}
              className="ml-auto rounded-sm px-1.5 py-0.5 text-zinc-300 hover:bg-violet-500/15 hover:text-zinc-100"
            >
              Revoir le run
            </button>
          </li>
        ))}
      </ul>
      {caches > 0 && (
        <button
          type="button"
          onClick={() => setDeplie((d) => !d)}
          className="mt-0.5 text-zinc-500 hover:text-zinc-300"
        >
          {deplie ? "Masquer" : `Afficher les ${caches} autres`}
        </button>
      )}
    </div>
  );
}
