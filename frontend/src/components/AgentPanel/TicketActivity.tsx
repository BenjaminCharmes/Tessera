import { useMemo, useState } from "react";
import { api } from "../../lib/api";
import { useResource } from "../../hooks/useResource";
import type { TicketActivity as Activity, Ticket } from "../../types/api";

interface TicketActivityProps {
  projectId: string | null;
  ticket: Ticket | null;
  /** Branche du dernier run, quand il y en a eu un dans cette session. */
  branch: string | null;
}

/**
 * Ce qu'un ticket a produit (ticket-064).
 *
 * L'information existait, éparpillée entre la base, le ticket et GitHub : il
 * fallait sortir de l'IDE et lire `git log` pour savoir ce qu'un ticket avait
 * réellement changé.
 *
 * L'ouverture de PR pousse la branche d'abord — GitHub refuse une `head`
 * qu'il ne connaît pas.
 *
 * Le merge, lui, dépend de ce que le projet déclare (ticket-082). Par défaut
 * il reste manuel : sur le dépôt d'un client, c'est le seul point où un humain
 * tranche, et c'est ce qui rend acceptable tout le reste de l'automatisation.
 */
export default function TicketActivity({
  projectId,
  ticket,
  branch,
}: TicketActivityProps) {
  const [busy, setBusy] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const ticketId = ticket?.id ?? null;

  // Une lecture qui échoue vaut « pas d'activité » : la section se tait.
  const fetcher = useMemo(
    () =>
      projectId && ticketId
        ? () => api.tickets.activity(projectId, ticketId)
        : null,
    [projectId, ticketId],
  );
  const { data: activity, refresh } = useResource<Activity | null>(
    fetcher,
    null,
  );

  async function mergePr() {
    if (!projectId || !ticketId) return;
    setBusy(true);
    setErrorMessage(null);
    try {
      await api.tickets.mergePr(projectId, ticketId);
      refresh();
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  async function openPr() {
    if (!projectId || !ticketId || !branch) return;
    setBusy(true);
    setErrorMessage(null);
    try {
      await api.tickets.openPr(projectId, ticketId, branch);
      refresh();
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  if (!ticket || !activity) return null;

  return (
    <section className="border-t border-zinc-800 px-3 py-2 text-xs">
      <h3 className="mb-1.5 font-medium uppercase tracking-wide text-zinc-500">
        Ce que ce ticket a produit
      </h3>

      {activity.runs.length === 0 ? (
        <p className="text-zinc-600">Aucun run pour l'instant.</p>
      ) : (
        <ul className="space-y-0.5">
          {activity.runs.map((run) => (
            <li key={run.id} className="flex items-baseline justify-between gap-2">
              <span
                className={
                  run.approved ? "text-green-400" : "text-amber-400"
                }
              >
                {run.approved ? "approuvé" : (run.final_status ?? "en cours")}
              </span>
              <span className="text-zinc-600 tabular-nums">
                {run.rounds ?? 0} tour(s) · {run.total_cost_usd.toFixed(3)} $
              </span>
            </li>
          ))}
        </ul>
      )}

      {branch && (
        <p className="mt-1.5 break-all text-zinc-500">
          Branche : <code>{branch}</code>
        </p>
      )}

      <div className="mt-2">
        {activity.pr_number ? (
          <div className="flex flex-wrap items-center gap-2">
            <p className="text-green-400">PR #{activity.pr_number} ouverte</p>
            {activity.autonomy === "merge" && (
              <button
                type="button"
                onClick={() => void mergePr()}
                disabled={busy}
                className="rounded-sm bg-zinc-700 px-2 py-1 text-zinc-100 hover:bg-zinc-600 disabled:opacity-40"
              >
                {busy ? "…" : "Merger si la CI est verte"}
              </button>
            )}
          </div>
        ) : (
          <>
            {/* Le bouton poussait la branche **puis** appelait l'API GitHub :
                sur un dépôt GitLab ou Azure, il poussait donc sans rien
                demander avant d'échouer. Sur le dépôt d'un client, pousser est
                précisément la décision qui ne se prend pas par mégarde
                (ticket-081). */}
            {activity.pr_supported === false ? (
              <p className="text-zinc-500">
                Dépôt hébergé sur {activity.forge ?? "une autre forge"} :
                l'ouverture de pull request n'est pas automatisée ici. La
                branche du ticket est prête, à pousser quand tu le décides.
              </p>
            ) : (
            <button
              type="button"
              onClick={() => void openPr()}
              disabled={busy || !branch}
              className="rounded-sm bg-zinc-700 px-2 py-1 text-zinc-100 hover:bg-zinc-600 disabled:opacity-40"
            >
              {busy ? "…" : "Pousser et ouvrir la PR"}
            </button>
            )}
            {!branch && (
              <p className="mt-1 text-zinc-600">
                Lance d'abord le pipeline : il n'y a pas encore de branche.
              </p>
            )}
          </>
        )}
        {activity.autonomy === "merge" ? (
          <p className="mt-1 text-zinc-600">
            Ce projet déclare `autonomy: merge` : l'IDE peut merger lui-même,
            mais seulement sur une CI verte.
          </p>
        ) : (
          <p className="mt-1 text-zinc-600">
            Le merge reste manuel — c'est la seule décision qui n'est pas
            automatisée. Un projet peut en décider autrement dans son
            agents.json.
          </p>
        )}
      </div>

      {errorMessage && (
        <p className="mt-1.5 wrap-break-word text-amber-300">{errorMessage}</p>
      )}
    </section>
  );
}
