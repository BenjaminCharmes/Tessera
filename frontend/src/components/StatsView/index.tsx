import { useMemo, useState } from "react";
import { api } from "../../lib/api";
import { useResource } from "../../hooks/useResource";
import RegionTitle from "../../design/RegionTitle";
import { BAND } from "../../design/layout";
import TimeBars from "../../design/charts/TimeBars";
import TimeLines from "../../design/charts/TimeLines";
import Donut from "../../design/charts/Donut";
import ShareBars from "../../design/charts/ShareBars";
import {
  formatCount,
  formatDay,
  formatDurationMs,
  formatUsd,
} from "../../design/charts/palette";
import type { RecentRun, StatsPeriod, UsageStats } from "../../types/api";
import Card from "./Card";
import KpiRow from "./KpiRow";
import QualityCard from "./QualityCard";
import RecentRuns from "./RecentRuns";
import RunHistorique from "./RunHistorique";

/**
 * Le tableau de statistiques — ticket-201. Remplace la ventilation seule de
 * ticket-077 : elle disait où part l'argent, jamais quand, ni si les runs
 * aboutissent, ni en combien de temps.
 *
 * Deux mesures d'unités différentes ne partagent jamais un axe : la dépense
 * et les tokens ont chacun leur graphique.
 *
 * La période et la portée sont remontées dans useCockpit (ticket-253) pour
 * que la colonne latérale les contrôle.
 */

interface StatsViewProps {
  /** `null` : tous projets confondus. */
  projectId: string | null;
  /** Nombre de jours de la période sélectionnée, géré par useCockpit. */
  days: StatsPeriod;
}

export default function StatsView({ projectId, days }: StatsViewProps) {
  const fetcher = useMemo(() => () => api.usage.stats(days, projectId), [days, projectId]);
  // Une lecture qui échoue vaut « pas de donnée » : la vue le dit.
  const { data, loading } = useResource<UsageStats | null>(fetcher, null);
  // Le run sélectionné dans l'historique — ouvre sa vue en lecture seule (ticket-281).
  const [selectedRun, setSelectedRun] = useState<RecentRun | null>(null);

  if (selectedRun) {
    return (
      <RunHistorique
        runId={selectedRun.id}
        ticketId={selectedRun.ticket_id}
        onClose={() => setSelectedRun(null)}
      />
    );
  }

  return (
    <div className="flex h-full flex-col bg-zinc-950">
      <div className={`${BAND} border-b border-zinc-700 bg-zinc-900 px-4`}>
        <RegionTitle>{projectId ? "Statistiques" : "Statistiques, tous projets"}</RegionTitle>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto p-4">
        {!data && (
          <p className="text-xs text-zinc-500">
            {loading ? "Chargement…" : "Statistiques indisponibles."}
          </p>
        )}
        {data && data.totals.runs === 0 && data.totals.cost_usd === 0 && (
          <p className="mb-4 rounded-lg border border-dashed border-zinc-800 px-4 py-3 text-xs text-zinc-500">
            Aucun run sur les {data.days} derniers jours. Les graphiques se rempliront au premier
            pipeline exécuté.
          </p>
        )}
        {data && <Dashboard data={data} onSelectRun={setSelectedRun} />}
      </div>
    </div>
  );
}

interface DashboardProps {
  data: UsageStats;
  onSelectRun: (run: RecentRun) => void;
}

function Dashboard({ data, onSelectRun }: DashboardProps) {
  const labels = data.daily.map((p) => formatDay(p.day));
  const global = data.project_id === null;
  return (
    <div className="space-y-4">
      <KpiRow totals={data.totals} quality={data.quality} />

      <div className="grid gap-4 xl:grid-cols-3">
        <Card title="Dépense par jour" aside="chat compris" className="xl:col-span-2">
          <TimeBars
            label="Dépense"
            points={data.daily.map((p, i) => ({ label: labels[i], value: p.cost_usd }))}
            format={formatUsd}
            empty="Aucune dépense sur la période."
          />
        </Card>
        <Card title="Dépense par agent">
          <Donut
            slices={data.per_agent.map((a) => ({ key: a.key, value: a.cost_usd }))}
            format={formatUsd}
            caption="au total"
            empty="Aucun appel d'agent."
          />
        </Card>
      </div>

      <div className="grid gap-4 xl:grid-cols-3">
        <Card title="Tokens par jour" aside="la lecture en cache est dans le total" className="xl:col-span-2">
          <TimeLines
            labels={labels}
            series={[
              { name: "Entrants hors cache", values: data.daily.map((p) => p.input_tokens) },
              { name: "Sortants", values: data.daily.map((p) => p.output_tokens) },
            ]}
            format={formatCount}
            empty="Aucun token sur la période."
          />
        </Card>
        <Card title="Issue des runs">
          <QualityCard quality={data.quality} />
        </Card>
      </div>

      <div className={`grid gap-4 ${global ? "xl:grid-cols-3" : "xl:grid-cols-2"}`}>
        {global && (
          <Card title="Dépense par projet">
            <ShareBars
              rows={data.per_project.map((p) => ({ key: p.key, value: p.cost_usd, detail: `${p.calls} appels` }))}
              format={formatUsd}
              empty="Aucun projet actif."
            />
          </Card>
        )}
        <Card title="Dépense par modèle">
          <ShareBars
            rows={data.per_model.map((m) => ({ key: m.key, value: m.cost_usd, detail: `${m.calls} appels` }))}
            format={formatUsd}
            empty="Aucun modèle appelé."
          />
        </Card>
        <Card title="Durée moyenne d'un appel" aside="par agent">
          <ShareBars
            rows={[...data.per_agent]
              .sort((a, b) => b.avg_duration_ms - a.avg_duration_ms)
              .map((a) => ({ key: a.key, value: a.avg_duration_ms }))}
            format={(ms) => formatDurationMs(ms)}
            scale="max"
            empty="Aucun appel d'agent."
          />
        </Card>
      </div>

      <Card title="Runs récents" aside={`${data.recent_runs.length} derniers`}>
        <RecentRuns runs={data.recent_runs} showProject={global} onSelect={onSelectRun} />
      </Card>
    </div>
  );
}
