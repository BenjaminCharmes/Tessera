import type { ProjectUsage, TicketUsage } from "../../types/api";

function formatTokens(n: number): string {
  return n.toLocaleString("fr-FR");
}

function formatCost(usd: number): string {
  if (usd === 0) return "$0.0000";
  if (usd < 0.0001) return "<$0.0001";
  return `$${usd.toFixed(4)}`;
}

interface SummaryCardProps {
  label: string;
  value: string;
}

function SummaryCard({ label, value }: SummaryCardProps) {
  return (
    <div className="flex flex-col gap-0.5 px-3 py-2 bg-zinc-800 rounded">
      <span className="text-[10px] text-zinc-500 uppercase tracking-wider">
        {label}
      </span>
      <span className="text-sm font-mono text-zinc-200">{value}</span>
    </div>
  );
}

interface TicketRowProps {
  ticket: TicketUsage;
  maxCost: number;
}

function TicketRow({ ticket, maxCost }: TicketRowProps) {
  const pct = maxCost > 0 ? (ticket.total_cost_usd / maxCost) * 100 : 0;
  return (
    <div className="py-1.5 border-b border-zinc-800 last:border-0">
      <div className="flex items-center justify-between gap-2 mb-1">
        <span className="text-[11px] font-mono text-zinc-300 truncate flex-1">
          {ticket.ticket_id}
        </span>
        <span className="shrink-0 text-[11px] font-mono text-amber-400">
          {formatCost(ticket.total_cost_usd)}
        </span>
      </div>
      <div className="w-full bg-zinc-800 rounded-full h-1">
        <div
          className="bg-amber-500 h-1 rounded-full transition-all"
          style={{ width: `${pct}%` }}
        />
      </div>
      <div className="flex gap-3 mt-1 text-[10px] text-zinc-600">
        <span>{formatTokens(ticket.input_tokens)} in</span>
        <span>{formatTokens(ticket.output_tokens)} out</span>
        <span>
          {ticket.call_count} appel{ticket.call_count > 1 ? "s" : ""}
        </span>
      </div>
    </div>
  );
}

interface UsageDashboardProps {
  usage: ProjectUsage | null;
  loading: boolean;
  error: string | null;
  onRefresh: () => void;
}

export default function UsageDashboard({
  usage,
  loading,
  error,
  onRefresh,
}: UsageDashboardProps) {
  if (loading) {
    return (
      <div className="p-4 text-zinc-500 text-xs">Chargement de l'usage…</div>
    );
  }

  if (error) {
    return <div className="p-4 text-red-400 text-xs">{error}</div>;
  }

  const maxCost = usage
    ? Math.max(...usage.per_ticket.map((t) => t.total_cost_usd), 0)
    : 0;

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-zinc-700 shrink-0">
        <span className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">
          Usage & Coût
        </span>
        <button
          onClick={onRefresh}
          className="text-[10px] text-zinc-500 hover:text-zinc-300 transition-colors"
          title="Rafraîchir"
        >
          ↺
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {/* Empty state */}
        {(!usage || usage.total_runs === 0) && (
          <p className="text-zinc-500 text-xs">
            Aucun pipeline exécuté — le coût s'affichera ici après le premier
            run.
          </p>
        )}

        {usage && usage.total_runs > 0 && (
          <>
            {/* Summary cards */}
            <div className="grid grid-cols-2 gap-2">
              <SummaryCard
                label="Coût total"
                value={formatCost(usage.total_cost_usd)}
              />
              <SummaryCard label="Runs" value={String(usage.total_runs)} />
              <SummaryCard
                label="Tokens"
                value={formatTokens(usage.total_tokens)}
              />
              <SummaryCard
                label="Coût / run"
                value={formatCost(usage.total_cost_usd / usage.total_runs)}
              />
            </div>

            {/* Per-ticket breakdown */}
            {usage.per_ticket.length > 0 && (
              <div>
                <div className="text-[10px] text-zinc-500 uppercase tracking-wider mb-2">
                  Par ticket
                </div>
                <div>
                  {usage.per_ticket.map((t) => (
                    <TicketRow key={t.ticket_id} ticket={t} maxCost={maxCost} />
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
