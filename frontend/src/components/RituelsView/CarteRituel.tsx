import { useState } from "react";
import type { Interruption, Rituel } from "../../lib/apiRituels";
import type { Project } from "../../types/api";
import Button from "../../design/ui/Button";
import { interruptionDe, libelleDeDate, libelleDuRetard, libelleDuRythme } from "./format";

interface CarteRituelProps {
  rituel: Rituel;
  projets: Project[];
  interruptions?: Interruption[];
  onOpenProject?: (p: Project) => void;
  onFait: (id: string) => void;
  onReporter: (id: string) => void;
}

/** La carte d'un rituel en retard : de quoi le faire, et le « Fait » (ticket-903). */
export default function CarteRituel({ rituel, projets, interruptions = [], onOpenProject, onFait, onReporter }: CarteRituelProps) {
  const [copie, setCopie] = useState(false);

  async function copier() {
    await navigator.clipboard.writeText(rituel.phrase);
    setCopie(true);
  }

  const retard = libelleDuRetard(rituel.derniere, new Date());
  const coupure = interruptionDe(rituel.derniere, interruptions);

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
      {retard ? (
        <p className="mt-1 text-xs text-zinc-400">
          {retard}
          {coupure
            ? ` · Tessera n'a pas tourné du ${libelleDeDate(coupure.debut)} au ${libelleDeDate(coupure.fin)}`
            : ""}
        </p>
      ) : null}
      <p className="mt-2 text-sm text-zinc-300">{rituel.detail}</p>
      <div className="mt-3 flex items-center gap-2">
        <code className="rounded bg-zinc-900 px-2 py-1 text-xs text-zinc-200">{rituel.phrase}</code>
        <Button taille="compact" onClick={() => void copier()}>
          {copie ? "Copié" : "Copier"}
        </Button>
      </div>
      <div className="mt-3 flex flex-wrap gap-2">
        {rituel.projets.map((id) => {
          const projet = projets.find((p) => p.id === id);
          return (
            <Button
              key={id}
              taille="compact"
              disabled={projet === undefined || onOpenProject === undefined}
              onClick={() => projet && onOpenProject?.(projet)}
            >
              Ouvrir {projet?.name ?? id}
            </Button>
          );
        })}
        <Button
          variante="plein"
          taille="compact"
          onClick={() => onFait(rituel.id)}
        >
          Fait
        </Button>
        <Button taille="compact" onClick={() => onReporter(rituel.id)}>
          Reporter à demain
        </Button>
      </div>
    </li>
  );
}
