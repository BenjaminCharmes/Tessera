import { useLimites } from "../../hooks/useLimites";

function montant(plafond: number | undefined): string {
  if (plafond === undefined) return "—";
  return plafond === 0 ? "aucun plafond" : `$${plafond.toFixed(2)}`;
}

/**
 * Les plafonds de dépense, en lecture — extraits de `PanneauUsage` pour que
 * la colonne de Statistiques et le panneau Réglages disent la même chose
 * (ticket-441).
 */
export default function PlafondsDeDepense() {
  const limites = useLimites();

  return (
    <section>
      <p className="mb-1.5 text-micro text-zinc-500">Plafonds de dépense</p>
      <dl className="space-y-1.5">
        <div className="flex justify-between text-xs">
          <dt className="text-zinc-400">Par run</dt>
          <dd className="font-mono text-zinc-200">
            {montant(limites?.run_max_budget_usd)}
          </dd>
        </div>
        <div className="flex justify-between text-xs">
          <dt className="text-zinc-400">Global</dt>
          <dd className="font-mono text-zinc-200">
            {montant(limites?.llm_max_budget_usd)}
          </dd>
        </div>
      </dl>
    </section>
  );
}
