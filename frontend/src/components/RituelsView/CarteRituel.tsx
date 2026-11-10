import { useState } from "react";
import type { Rituel } from "../../lib/apiRituels";
import type { Project } from "../../types/api";
import { libelleDeDate, libelleDuRythme } from "./format";

interface CarteRituelProps {
  rituel: Rituel;
  projets: Project[];
  onOpenProject?: (p: Project) => void;
  onFait: (id: string) => void;
  onReporter: (id: string) => void;
}

const BOUTON = "rounded-md border border-zinc-700 px-2.5 py-1 text-xs text-zinc-200 hover:bg-zinc-800";

/** La carte d'un rituel en retard : de quoi le faire, et le « Fait » (ticket-903). */
export default function CarteRituel({ rituel, projets, onOpenProject, onFait, onReporter }: CarteRituelProps) {
  const [copie, setCopie] = useState(false);

  async function copier() {
    await navigator.clipboard.writeText(rituel.phrase);
    setCopie(true);
  }

  return (
    <li className="rounded-lg border border-zinc-700 bg-zinc-800/50 p-4">
      <div className="flex items-baseline justify-between gap-3">
        <h3 className="text-sm font-medium text-zinc-100">{rituel.titre}</h3>
        <span className={`text-xs ${rituel.depasse ? "text-red-300" : "text-amber-300"}`}>
          {rituel.depasse ? "Dépassé, depuis " : "Depuis "}
          {libelleDeDate(rituel.derniere)}
        </span>
      </div>
      <p className="mt-1 text-xs text-zinc-400">
        {libelleDuRythme(rituel.rythme)} · {rituel.duree_min} min
      </p>
      <p className="mt-2 text-sm text-zinc-300">{rituel.detail}</p>
      <div className="mt-3 flex items-center gap-2">
        <code className="rounded bg-zinc-900 px-2 py-1 text-xs text-zinc-200">{rituel.phrase}</code>
        <button type="button" className={BOUTON} onClick={() => void copier()}>
          {copie ? "Copié" : "Copier"}
        </button>
      </div>
      <div className="mt-3 flex flex-wrap gap-2">
        {rituel.projets.map((id) => {
          const projet = projets.find((p) => p.id === id);
          return (
            <button
              key={id}
              type="button"
              className={`${BOUTON} disabled:opacity-40`}
              disabled={projet === undefined || onOpenProject === undefined}
              onClick={() => projet && onOpenProject?.(projet)}
            >
              Ouvrir {projet?.name ?? id}
            </button>
          );
        })}
        <button
          type="button"
          className="rounded-md bg-violet-600 px-2.5 py-1 text-xs font-medium text-white hover:bg-violet-500"
          onClick={() => onFait(rituel.id)}
        >
          Fait
        </button>
        <button type="button" className={BOUTON} onClick={() => onReporter(rituel.id)}>
          Reporter à demain
        </button>
      </div>
    </li>
  );
}
