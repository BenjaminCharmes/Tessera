import { useLimites } from "../../hooks/useLimites";
import type { StatsPeriod } from "../../types/api";

const PERIODS: StatsPeriod[] = [7, 30, 90];

interface PanneauUsageProps {
  days: StatsPeriod;
  setDays: (d: StatsPeriod) => void;
  portee: "projet" | "tous";
  setPortee: (p: "projet" | "tous") => void;
  /** Null when no project is active — "Ce projet" button is then disabled. */
  projetActifId: string | null;
}

/**
 * Les réglages de la vue Statistiques, dans la colonne latérale — ticket-253.
 *
 * Trois blocs empilés : période, portée, plafonds. La vue centrale
 * (StatsView) reçoit les valeurs résultantes en props ; elle ne porte plus
 * d'état interne sur ces deux dimensions.
 */
export default function PanneauUsage({
  days,
  setDays,
  portee,
  setPortee,
  projetActifId,
}: PanneauUsageProps) {
  const limites = useLimites();

  return (
    <div className="flex flex-col gap-4 px-3 py-3">
      {/* Bloc 1 : Période */}
      <section>
        <p className="mb-1.5 text-micro text-zinc-500">jours UTC</p>
        <div
          className="flex rounded border border-zinc-700 p-0.5"
          role="group"
          aria-label="Période"
        >
          {PERIODS.map((p) => (
            <button
              key={p}
              type="button"
              aria-pressed={days === p}
              onClick={() => setDays(p)}
              className={`flex-1 rounded-sm px-2 py-0.5 text-mini ${
                days === p
                  ? "bg-zinc-700 text-zinc-100"
                  : "text-zinc-400 hover:text-zinc-200"
              }`}
            >
              {p} j
            </button>
          ))}
        </div>
      </section>

      {/* Bloc 2 : Portée */}
      <section>
        <p className="mb-1.5 text-micro text-zinc-500">Portée</p>
        <div
          className="flex rounded border border-zinc-700 p-0.5"
          role="group"
          aria-label="Portée"
        >
          <button
            type="button"
            aria-pressed={portee === "projet"}
            disabled={projetActifId === null}
            onClick={() => setPortee("projet")}
            className={`flex-1 rounded-sm px-2 py-0.5 text-mini disabled:cursor-not-allowed disabled:text-zinc-600 ${
              portee === "projet"
                ? "bg-zinc-700 text-zinc-100"
                : "text-zinc-400 hover:text-zinc-200"
            }`}
          >
            Ce projet
          </button>
          <button
            type="button"
            aria-pressed={portee === "tous"}
            onClick={() => setPortee("tous")}
            className={`flex-1 rounded-sm px-2 py-0.5 text-mini ${
              portee === "tous"
                ? "bg-zinc-700 text-zinc-100"
                : "text-zinc-400 hover:text-zinc-200"
            }`}
          >
            Tous les projets
          </button>
        </div>
      </section>

      {/* Bloc 3 : Plafonds */}
      <section>
        <p className="mb-1.5 text-micro text-zinc-500">Plafonds de dépense</p>
        <dl className="space-y-1.5">
          <div className="flex justify-between text-xs">
            <dt className="text-zinc-400">Par run</dt>
            <dd className="font-mono text-zinc-200">
              {limites === null
                ? "—"
                : limites.run_max_budget_usd === 0
                  ? "aucun plafond"
                  : `$${limites.run_max_budget_usd.toFixed(2)}`}
            </dd>
          </div>
          <div className="flex justify-between text-xs">
            <dt className="text-zinc-400">Global</dt>
            <dd className="font-mono text-zinc-200">
              {limites === null
                ? "—"
                : limites.llm_max_budget_usd === 0
                  ? "aucun plafond"
                  : `$${limites.llm_max_budget_usd.toFixed(2)}`}
            </dd>
          </div>
        </dl>
      </section>
    </div>
  );
}
