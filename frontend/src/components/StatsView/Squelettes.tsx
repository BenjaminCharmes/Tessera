/*
 * Les squelettes du tableau de statistiques — ticket-735. Pendant la lecture, la
 * page garde sa forme : six tuiles de chiffres clés, puis les cartes des
 * graphiques. Sans eux, le quota apparaissait seul et la page sautait à l'arrivée
 * des données. La pulsation s'arrête sous `prefers-reduced-motion`.
 */

const BLOC = "rounded-xl border border-zinc-800/80 bg-zinc-900/70 motion-safe:animate-pulse";

/** Les six tuiles des chiffres clés, à la place de `KpiRow`. */
export function TuilesSquelettes() {
  return (
    <div data-squelette="kpi" className="grid grid-cols-2 gap-3 md:grid-cols-3" aria-hidden="true">
      {Array.from({ length: 6 }, (_, i) => (
        <div key={i} className={`${BLOC} h-[88px]`} />
      ))}
    </div>
  );
}

/** Les deux premières rangées de cartes, à la place du tableau. */
export function CartesSquelettes() {
  return (
    <div data-squelette="cartes" className="space-y-4" aria-hidden="true">
      {[0, 1].map((rangee) => (
        <div key={rangee} className="grid gap-4 xl:grid-cols-3">
          <div className={`${BLOC} h-72 xl:col-span-2`} />
          <div className={`${BLOC} h-72`} />
        </div>
      ))}
    </div>
  );
}
