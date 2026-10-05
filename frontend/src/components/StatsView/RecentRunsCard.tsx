import { useEffect, useMemo, useState } from "react";
import { api } from "../../lib/api";
import { useResource } from "../../hooks/useResource";
import type { RecentRun, StatsPeriod } from "../../types/api";
import Card from "./Card";
import RecentRuns from "./RecentRuns";

/** Ce que les statistiques chargent d'emblée (`RECENT_RUNS_LIMIT`). */
const PREMIERS = 10;
const PAS = 20;
const ATTENTE_MS = 300;

interface RecentRunsCardProps {
  /** Les runs déjà rendus par `/usage/stats`. */
  initial: RecentRun[];
  days: StatsPeriod;
  projectId: string | null;
  onSelect: (run: RecentRun) => void;
}

/**
 * La carte « Runs récents », avec une recherche et « Afficher plus » —
 * ticket-335.
 *
 * Tant qu'on n'y touche pas, elle montre les dix runs venus avec les
 * statistiques, sans requête de plus. Chercher ou en demander davantage
 * passe par `/usage/recent-runs`, qui ne recalcule pas tout l'écran. La
 * recherche part quand la frappe s'arrête, pas à chaque caractère.
 */
export default function RecentRunsCard({ initial, days, projectId, onSelect }: RecentRunsCardProps) {
  const [saisie, setSaisie] = useState("");
  const [recherche, setRecherche] = useState("");
  const [limite, setLimite] = useState(PREMIERS);

  useEffect(() => {
    const minuteur = setTimeout(() => setRecherche(saisie.trim()), ATTENTE_MS);
    return () => clearTimeout(minuteur);
  }, [saisie]);

  const fetcher = useMemo(
    () =>
      recherche === "" && limite === PREMIERS
        ? null
        : () => api.usage.recentRuns(days, projectId, limite, recherche),
    [days, projectId, limite, recherche],
  );
  const lecture = useResource<RecentRun[] | null>(fetcher, null);
  const runs = fetcher === null ? initial : (lecture.data ?? []);
  const enCours = fetcher !== null && lecture.loading;

  return (
    <Card title="Runs récents" aside={enCours ? "chargement…" : `${runs.length} affichés`}>
      <input
        type="search"
        aria-label="Chercher un run"
        placeholder="Ticket ou projet…"
        value={saisie}
        onChange={(e) => setSaisie(e.target.value)}
        className="mb-3 w-full max-w-xs rounded-sm border border-zinc-700 bg-zinc-950 px-2 py-1 text-xs text-zinc-200 placeholder:text-zinc-600 focus:border-violet-500 focus:outline-none"
      />
      {!enCours && (
        <RecentRuns
          runs={runs}
          showProject={projectId === null}
          onSelect={onSelect}
          vide={recherche ? `Aucun run ne correspond à « ${recherche} ».` : undefined}
        />
      )}
      {!enCours && runs.length >= limite && (
        <button
          type="button"
          onClick={() => setLimite((l) => l + PAS)}
          className="mt-2 text-xs text-zinc-400 hover:text-zinc-200"
        >
          Afficher plus
        </button>
      )}
    </Card>
  );
}
