import { useEffect, useState } from "react";
import { api } from "../../lib/api";
import RegionTitle from "../../design/RegionTitle";
import { BAND } from "../../design/layout";
import type { VentilationDesCouts } from "../../types/api";

/**
 * Où part l'argent — ticket-077.
 *
 * Le panneau latéral donnait déjà le total, les runs et la dépense par ticket.
 * Il manquait la ventilation qui permet d'**agir** : par agent, parce qu'elle
 * dit qui consomme — un codeur qui mange 70 % du budget, ou un reviewer plus
 * cher que prévu parce qu'il relit tout le diff à chaque tour — et par modèle,
 * pour préparer l'arbitrage du jour où l'on descend un agent en Haiku.
 *
 * Les parts sont calculées sur le total réel et affichées en pourcentage : sur
 * des montants de quelques centimes, un nombre absolu ne dit rien, alors qu'une
 * part se lit tout de suite.
 */
interface CostViewProps {
  /** `null` : la vue d'ensemble, tous projets confondus (ticket-082). */
  projectId: string | null;
}

function formatCout(usd: number): string {
  return usd < 0.01 ? `${(usd * 100).toFixed(2)} ¢` : `${usd.toFixed(3)} $`;
}

function Ligne({
  nom,
  cout,
  total,
  appels,
}: {
  nom: string;
  cout: number;
  total: number;
  appels: number;
}) {
  const part = total > 0 ? (cout / total) * 100 : 0;
  return (
    <li className="px-4 py-1.5">
      <div className="mb-1 flex items-baseline justify-between gap-2 text-xs">
        <span className="truncate font-mono text-zinc-200">{nom}</span>
        <span className="shrink-0 text-zinc-400">
          {formatCout(cout)} · {part.toFixed(0)} % · {appels} appel
          {appels > 1 ? "s" : ""}
        </span>
      </div>
      <div className="h-1 overflow-hidden rounded-sm bg-zinc-800">
        <div className="h-full bg-violet-400" style={{ width: `${part}%` }} />
      </div>
    </li>
  );
}

export default function CostView({ projectId }: CostViewProps) {
  const [data, setData] = useState<VentilationDesCouts | null>(null);

  useEffect(() => {
    let annule = false;
    setData(null);
    void (async () => {
      try {
        const d = projectId
          ? await api.usage.breakdown(projectId)
          : await api.usage.breakdownGlobal();
        if (!annule) setData(d);
      } catch {
        if (!annule) setData(null);
      }
    })();
    return () => {
      annule = true;
    };
  }, [projectId]);

  const vide =
    data !== null &&
    data.per_agent.length === 0 &&
    data.per_model.length === 0 &&
    data.per_project.length === 0;

  return (
    <div className="flex h-full flex-col bg-zinc-900">
      <div className={`${BAND} justify-between gap-3 border-b border-zinc-700 px-4`}>
        <RegionTitle>
          {projectId ? "Où part la dépense" : "Dépense, tous projets"}
        </RegionTitle>
        {data && (
          <span className="text-mini text-zinc-400">
            {formatCout(data.total_cost_usd)} au total
          </span>
        )}
      </div>

      {vide && (
        <p className="px-4 py-3 text-xs text-zinc-500">
          Aucun appel d'agent enregistré pour ce projet.
        </p>
      )}

      {data && !vide && (
        <div className="min-h-0 flex-1 overflow-y-auto py-2">
          {data.per_project.length > 0 && (
            <>
              <p className="px-4 pb-1 text-mini uppercase tracking-wider text-zinc-500">
                Par projet
              </p>
              <ul>
                {data.per_project.map((p) => (
                  <Ligne
                    key={p.project_id}
                    nom={p.project_id}
                    cout={p.total_cost_usd}
                    total={data.total_cost_usd}
                    appels={p.call_count}
                  />
                ))}
              </ul>
            </>
          )}

          <p className="px-4 pb-1 pt-3 text-mini uppercase tracking-wider text-zinc-500">
            Par agent
          </p>
          <ul>
            {data.per_agent.map((a) => (
              <Ligne
                key={a.role}
                nom={a.role}
                cout={a.total_cost_usd}
                total={data.total_cost_usd}
                appels={a.call_count}
              />
            ))}
          </ul>

          <p className="px-4 pb-1 pt-3 text-mini uppercase tracking-wider text-zinc-500">
            Par modèle
          </p>
          <ul>
            {data.per_model.map((m) => (
              <Ligne
                key={m.model}
                nom={m.model}
                cout={m.total_cost_usd}
                total={data.total_cost_usd}
                appels={m.call_count}
              />
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
